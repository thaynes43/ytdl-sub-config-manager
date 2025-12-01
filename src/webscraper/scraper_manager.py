"""Generic web scraper manager with dependency injection."""

import time
from typing import Dict, List, Optional, Set
from pathlib import Path
from http.cookiejar import MozillaCookieJar, Cookie
from ..core.logging import get_logger
from .models import ScrapingConfig, ScrapingResult, ScrapingStatus
from .session_manager import SessionManager
from .scraper_strategy import ScraperStrategy


class ScraperManager:
    """Generic web scraper manager that coordinates session and scraping strategies."""
    
    def __init__(self, session_manager: SessionManager, scraper_strategy: ScraperStrategy):
        """
        Initialize the scraper manager.
        
        Args:
            session_manager: Session management strategy
            scraper_strategy: Website-specific scraping strategy
        """
        self.session_manager = session_manager
        self.scraper_strategy = scraper_strategy
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def _save_auth_artifacts(self, media_dir: str, class_player_url: Optional[str] = None) -> None:
        """
        Save cookies and bearer token to media directory.
        
        Args:
            media_dir: Directory where files will be saved
            class_player_url: Optional URL to a class player page to navigate to first
                            (bearer token may only be available on class pages)
        """
        try:
            auth_dir = Path(media_dir)
            auth_dir.mkdir(parents=True, exist_ok=True)
            
            driver = self.session_manager.driver
            if not driver:
                self.logger.warning("No active driver to save auth artifacts")
                return

            token = None

            # Navigate to class player page if provided (bearer token is in network request headers)
            if class_player_url:
                self.logger.info(f"Navigating to class player page to retrieve bearer token: {class_player_url}")
                
                # Enable network and performance domains to capture request headers via CDP
                driver.execute_cdp_cmd('Network.enable', {})
                driver.execute_cdp_cmd('Performance.enable', {})
                driver.execute_cdp_cmd('Page.enable', {})
                self.logger.debug("Network, Performance, and Page domains enabled")
                
                # Store captured token
                captured_token = [None]
                
                # Use more aggressive JavaScript interception with better logging
                intercept_script = """
                (function() {
                    window._capturedBearerToken = null;
                    window._interceptionLog = [];
                    
                    // Intercept fetch - more comprehensive
                    const originalFetch = window.fetch;
                    window.fetch = function(...args) {
                        const url = typeof args[0] === 'string' ? args[0] : (args[0] ? args[0].url : '');
                        const options = args[1] || {};
                        
                        window._interceptionLog.push('fetch: ' + url);
                        
                        if (url && url.includes('api.onepeloton.com')) {
                            const headers = options.headers || {};
                            const authHeader = headers.Authorization || headers.authorization;
                            window._interceptionLog.push('fetch headers: ' + JSON.stringify(Object.keys(headers)));
                            if (authHeader && authHeader.startsWith('Bearer ')) {
                                window._capturedBearerToken = authHeader;
                                window._interceptionLog.push('TOKEN CAPTURED FROM FETCH');
                            }
                        }
                        
                        return originalFetch.apply(this, args);
                    };
                    
                    // Intercept XMLHttpRequest - more comprehensive
                    const originalOpen = XMLHttpRequest.prototype.open;
                    const originalSetRequestHeader = XMLHttpRequest.prototype.setRequestHeader;
                    const originalSend = XMLHttpRequest.prototype.send;
                    
                    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
                        this._url = url;
                        this._method = method;
                        this._headers = {};
                        window._interceptionLog.push('XHR open: ' + method + ' ' + url);
                        return originalOpen.apply(this, [method, url, ...rest]);
                    };
                    
                    XMLHttpRequest.prototype.setRequestHeader = function(header, value) {
                        this._headers = this._headers || {};
                        this._headers[header] = value;
                        
                        if (header.toLowerCase() === 'authorization' && value && value.startsWith('Bearer ')) {
                            if (this._url && this._url.includes('api.onepeloton.com')) {
                                window._capturedBearerToken = value;
                                window._interceptionLog.push('TOKEN CAPTURED FROM XHR: ' + this._url);
                            }
                        }
                        return originalSetRequestHeader.apply(this, [header, value]);
                    };
                    
                    XMLHttpRequest.prototype.send = function(...args) {
                        if (this._url && this._url.includes('api.onepeloton.com')) {
                            window._interceptionLog.push('XHR send: ' + this._url + ' headers: ' + JSON.stringify(this._headers));
                        }
                        return originalSend.apply(this, args);
                    };
                })();
                """
                
                # Inject script to run on new document creation
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': intercept_script})
                self.logger.debug("JavaScript interception script added to run on new document")
                
                # Navigate to page
                driver.get(class_player_url)
                self.logger.debug("Navigated to class player page, waiting for network requests...")
                
                # Wait for network requests to be made (the video metrics request happens after page load)
                max_wait = 15
                wait_interval = 0.5
                waited = 0
                while waited < max_wait:
                    time.sleep(wait_interval)
                    waited += wait_interval
                    
                    # Check interception log
                    try:
                        log = driver.execute_script("return window._interceptionLog || [];")
                        if log:
                            self.logger.debug(f"Interception log (after {waited}s): {log[-5:]}")  # Last 5 entries
                    except:
                        pass
                    
                    # Check if token was captured
                    token = driver.execute_script("return window._capturedBearerToken;")
                    if token:
                        captured_token[0] = token
                        self.logger.info("Captured bearer token from network request")
                        break
                    
                    # Also try to get from CDP performance logs
                    try:
                        logs = driver.get_log('performance')
                        self.logger.debug(f"Found {len(logs)} performance log entries")
                        for log_entry in logs[-20:]:  # Check last 20 log entries
                            message = log_entry.get('message', '')
                            if 'api.onepeloton.com' in message and 'metrics' in message:
                                self.logger.debug(f"Found relevant log entry: {message[:200]}")
                                import json
                                try:
                                    log_data = json.loads(message)
                                    if 'message' in log_data:
                                        msg = log_data['message']
                                        method = msg.get('method', '')
                                        
                                        # Check for Network.requestWillBeSent event
                                        if method == 'Network.requestWillBeSent' and 'params' in msg:
                                            params = msg['params']
                                            request = params.get('request', {})
                                            url = request.get('url', '')
                                            if 'api.onepeloton.com/api/metrics/v2/video' in url:
                                                headers = request.get('headers', {})
                                                auth_header = headers.get('Authorization') or headers.get('authorization')
                                                if auth_header and auth_header.startswith('Bearer '):
                                                    captured_token[0] = auth_header
                                                    self.logger.info("Captured bearer token from performance logs")
                                                    break
                                except json.JSONDecodeError:
                                    continue
                        if captured_token[0]:
                            break
                    except Exception as e:
                        self.logger.debug(f"Error reading performance logs: {e}")
                
                if not captured_token[0]:
                    # Get final interception log for debugging
                    try:
                        final_log = driver.execute_script("return window._interceptionLog || [];")
                        self.logger.warning(f"Token not captured. Interception log: {final_log}")
                    except:
                        pass
                
                # Disable network domain
                try:
                    driver.execute_cdp_cmd('Network.disable', {})
                except:
                    pass
                
                token = captured_token[0]

            # Save cookies
            cookies_path = auth_dir / "cookies.txt"
            self.logger.info(f"Saving cookies to {cookies_path}")
            jar = MozillaCookieJar(str(cookies_path))
            
            for cookie in driver.get_cookies():
                c = Cookie(
                    version=0,
                    name=cookie['name'],
                    value=cookie['value'],
                    port=None,
                    port_specified=False,
                    domain=cookie['domain'],
                    domain_specified=bool(cookie.get('domain')),
                    domain_initial_dot=bool(cookie.get('domain', '').startswith('.')),
                    path=cookie['path'],
                    path_specified=bool(cookie.get('path')),
                    secure=cookie['secure'],
                    expires=cookie.get('expiry'),
                    discard=False,
                    comment=None,
                    comment_url=None,
                    rest={'HttpOnly': str(cookie.get('httpOnly'))} if cookie.get('httpOnly') is not None else {},
                    rfc2109=False,
                )
                jar.set_cookie(c)
            
            jar.save(ignore_discard=True, ignore_expires=True)
            
            # Save bearer token
            if token:
                bearer_path = auth_dir / "bearer.txt"
                self.logger.info(f"Saving bearer token to {bearer_path}")
                bearer_path.write_text(token.strip())
            else:
                self.logger.warning("Bearer token not found in network requests - bearer token will not be saved")
                
        except Exception as e:
            self.logger.error(f"Failed to save auth artifacts: {e}")

    def scrape_activities(self, username: str, password: str, activities: List[str], 
                         configs: Dict[str, ScrapingConfig], media_dir: Optional[str] = None) -> Dict[str, ScrapingResult]:
        """
        Scrape multiple activities in a single session.
        
        Args:
            username: Login username
            password: Login password
            activities: List of activity names to scrape
            configs: Configuration for each activity
            media_dir: Optional directory to save authentication artifacts (cookies/bearer token)
            
        Returns:
            Dictionary mapping activity names to scraping results
        """
        results = {}
        
        try:
            # Update session manager settings based on first config (assuming all configs have same settings)
            if configs:
                first_config = next(iter(configs.values()))
                self.session_manager.headless = first_config.headless
                self.session_manager.container_mode = first_config.container_mode
            
            # Create session and login
            self.logger.info("Creating browser session")
            driver = self.session_manager.create_session()
            
            self.logger.info("Logging in")
            if not self.session_manager.login(username, password):
                raise RuntimeError("Login failed")
            
            # Track if we've saved auth artifacts yet
            auth_artifacts_saved = False
            
            # Scrape each activity
            for activity in activities:
                self.logger.info(f"Starting scrape for activity: {activity}")
                
                if activity not in configs:
                    self.logger.error(f"No configuration found for activity: {activity}")
                    results[activity] = ScrapingResult(
                        activity=activity,
                        classes=[],
                        total_found=0,
                        total_skipped=0,
                        total_errors=1,
                        status=ScrapingStatus.FAILED,
                        error_message=f"No configuration found for activity: {activity}"
                    )
                    continue
                
                try:
                    result = self.scraper_strategy.scrape_activity(driver, configs[activity])
                    results[activity] = result
                    
                    # Save auth artifacts after first successful scrape (we now have a class player URL)
                    if media_dir and not auth_artifacts_saved and result.classes:
                        first_class = result.classes[0]
                        if hasattr(first_class, 'player_url') and first_class.player_url:
                            self.logger.info("Saving auth artifacts from first class player page")
                            self._save_auth_artifacts(media_dir, first_class.player_url)
                            auth_artifacts_saved = True
                    
                    self.logger.info(f"Completed scrape for {activity}: "
                                   f"{len(result.classes)} classes, "
                                   f"{result.total_skipped} skipped, "
                                   f"{result.total_errors} errors")
                    
                except Exception as e:
                    self.logger.error(f"Error scraping activity {activity}: {e}")
                    results[activity] = ScrapingResult(
                        activity=activity,
                        classes=[],
                        total_found=0,
                        total_skipped=0,
                        total_errors=1,
                        status=ScrapingStatus.FAILED,
                        error_message=str(e)
                    )
        
        except Exception as e:
            self.logger.error(f"Fatal error during scraping session: {e}")
            # Create failed results for all activities
            for activity in activities:
                if activity not in results:
                    results[activity] = ScrapingResult(
                        activity=activity,
                        classes=[],
                        total_found=0,
                        total_skipped=0,
                        total_errors=1,
                        status=ScrapingStatus.FAILED,
                        error_message=f"Session error: {str(e)}"
                    )
        
        finally:
            # Save auth artifacts if we haven't yet (fallback - try without class page)
            if media_dir and not auth_artifacts_saved:
                self.logger.info("Saving auth artifacts (no class page available)")
                self._save_auth_artifacts(media_dir)
            
            # Always close the session
            self.logger.info("Closing browser session")
            self.session_manager.close_session()
        
        return results
    
    def scrape_single_activity(self, username: str, password: str, 
                              activity: str, config: ScrapingConfig) -> ScrapingResult:
        """
        Scrape a single activity.
        
        Args:
            username: Login username
            password: Login password
            activity: Activity name to scrape
            config: Scraping configuration
            
        Returns:
            ScrapingResult for the activity
        """
        results = self.scrape_activities(username, password, [activity], {activity: config})
        return results[activity]
