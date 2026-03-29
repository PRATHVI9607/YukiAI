"""
Browser control module.

Opens URLs and performs web searches using the default browser.
"""

import webbrowser
import logging
from typing import Dict, Any
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class BrowserCtrl:
    """
    Browser controller for opening URLs and searching.
    
    Features:
    - Open URLs in default browser
    - Perform Google searches
    - Simple, no undo needed
    """
    
    def __init__(self):
        """Initialize browser controller."""
        logger.info("BrowserCtrl initialized")
    
    def open_url(self, url: str) -> Dict[str, Any]:
        """
        Open a URL in the default browser.
        
        Args:
            url: URL to open
        
        Returns:
            Result dict with success status and message
        """
        if not url:
            return {
                "success": False,
                "message": "...you need to specify a URL."
            }
        
        url = url.strip()
        
        # Add https:// if no protocol specified
        if not url.startswith(('http://', 'https://', 'file://', 'ftp://')):
            url = f"https://{url}"
        
        try:
            webbrowser.open(url)
            logger.info(f"Opened URL: {url}")
            
            return {
                "success": True,
                "message": f"Done. Opening {url}."
            }
        
        except Exception as e:
            logger.error(f"Error opening URL: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong opening that URL."
            }
    
    def search(self, query: str) -> Dict[str, Any]:
        """
        Perform a Google search.
        
        Args:
            query: Search query
        
        Returns:
            Result dict with success status and message
        """
        if not query:
            return {
                "success": False,
                "message": "...you need to specify a search query."
            }
        
        query = query.strip()
        
        try:
            # Encode query for URL
            encoded_query = quote_plus(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            
            webbrowser.open(search_url)
            logger.info(f"Performed search: {query}")
            
            return {
                "success": True,
                "message": f"Done. Searching for '{query}'."
            }
        
        except Exception as e:
            logger.error(f"Error performing search: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong with the search."
            }
    
    def open_youtube(self, query: str = "") -> Dict[str, Any]:
        """
        Open YouTube, optionally with a search query.
        
        Args:
            query: Optional search query
        
        Returns:
            Result dict with success status and message
        """
        try:
            if query:
                encoded_query = quote_plus(query.strip())
                url = f"https://www.youtube.com/results?search_query={encoded_query}"
                message = f"Done. Searching YouTube for '{query}'."
            else:
                url = "https://www.youtube.com"
                message = "Done. Opening YouTube."
            
            webbrowser.open(url)
            logger.info(f"Opened YouTube: {url}")
            
            return {
                "success": True,
                "message": message
            }
        
        except Exception as e:
            logger.error(f"Error opening YouTube: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong opening YouTube."
            }
    
    def open_github(self, repo: str = "") -> Dict[str, Any]:
        """
        Open GitHub, optionally navigating to a specific repository.
        
        Args:
            repo: Optional repository in format "owner/repo"
        
        Returns:
            Result dict with success status and message
        """
        try:
            if repo:
                repo = repo.strip().strip('/')
                url = f"https://github.com/{repo}"
                message = f"Done. Opening {repo} on GitHub."
            else:
                url = "https://github.com"
                message = "Done. Opening GitHub."
            
            webbrowser.open(url)
            logger.info(f"Opened GitHub: {url}")
            
            return {
                "success": True,
                "message": message
            }
        
        except Exception as e:
            logger.error(f"Error opening GitHub: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong opening GitHub."
            }
    
    def open_reddit(self, subreddit: str = "") -> Dict[str, Any]:
        """
        Open Reddit, optionally navigating to a specific subreddit.
        
        Args:
            subreddit: Optional subreddit name
        
        Returns:
            Result dict with success status and message
        """
        try:
            if subreddit:
                subreddit = subreddit.strip().strip('/')
                # Remove r/ prefix if present
                if subreddit.startswith('r/'):
                    subreddit = subreddit[2:]
                
                url = f"https://www.reddit.com/r/{subreddit}"
                message = f"Done. Opening r/{subreddit}."
            else:
                url = "https://www.reddit.com"
                message = "Done. Opening Reddit."
            
            webbrowser.open(url)
            logger.info(f"Opened Reddit: {url}")
            
            return {
                "success": True,
                "message": message
            }
        
        except Exception as e:
            logger.error(f"Error opening Reddit: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong opening Reddit."
            }
    
    def open_twitter(self, user: str = "") -> Dict[str, Any]:
        """
        Open Twitter/X, optionally navigating to a specific user.
        
        Args:
            user: Optional username
        
        Returns:
            Result dict with success status and message
        """
        try:
            if user:
                user = user.strip().strip('@')
                url = f"https://twitter.com/{user}"
                message = f"Done. Opening @{user} on Twitter."
            else:
                url = "https://twitter.com"
                message = "Done. Opening Twitter."
            
            webbrowser.open(url)
            logger.info(f"Opened Twitter: {url}")
            
            return {
                "success": True,
                "message": message
            }
        
        except Exception as e:
            logger.error(f"Error opening Twitter: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong opening Twitter."
            }


def create_browser_ctrl() -> BrowserCtrl:
    """
    Factory function to create BrowserCtrl instance.
    
    Returns:
        Initialized BrowserCtrl instance
    """
    return BrowserCtrl()
