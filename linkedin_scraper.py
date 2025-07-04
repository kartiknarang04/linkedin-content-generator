import os
import sys
import time
import random
import re
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv
from uuid import uuid4
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LinkedInScraper:
    # Add this complete __init__ method to your LinkedInScraper class:

    def __init__(self, headless=False, debug=True, max_posts=50, chroma_db_path="chroma_db"):
        """Initialize the LinkedIn scraper with login credentials and ChromaDB."""
        
        # Set instance variables
        self.headless = headless
        self.debug = debug
        self.max_posts = max_posts
        self.logged_in = False
        self.session_id = str(uuid4())[:8]
        
        # Get credentials from environment
        self.email = os.getenv('LINKEDIN_EMAIL')
        self.password = os.getenv('LINKEDIN_PASSWORD')
        
        if not self.email or not self.password:
            raise ValueError("LinkedIn credentials not found in environment variables")
        
        # Create debug directory
        if self.debug:
            os.makedirs('debug', exist_ok=True)
        
        # Initialize WebDriver
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            logger.info("WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise e
        
        # Add ChromaDB initialization
        self.chroma_db_path = chroma_db_path
        self.chroma_client = chromadb.PersistentClient(path=chroma_db_path)
        
        # Initialize sentence transformer for embeddings
        logger.info("Loading sentence transformer model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Sentence transformer model loaded successfully")
        
        # Initialize or get collection
        try:
            self.collection = self.chroma_client.get_collection(name="posts_collection")
            logger.info("Connected to existing ChromaDB collection")
        except:
            self.collection = self.chroma_client.create_collection(name="posts_collection")
            logger.info("Created new ChromaDB collection")
        
    def login(self):
        """Log in to LinkedIn."""
        try:
            logger.info("Navigating to LinkedIn login page")
            self.driver.get('https://www.linkedin.com/login')
            time.sleep(3)
            
            # Take screenshot of login page
            if self.debug:
                self.driver.save_screenshot(f'debug/{self.session_id}_login_page.png')
            
            # Wait for login page to load
            self.wait.until(EC.presence_of_element_located((By.ID, 'username')))
            
            # Enter email
            username_field = self.driver.find_element(By.ID, 'username')
            username_field.clear()
            username_field.send_keys(self.email)
            
            # Enter password
            password_field = self.driver.find_element(By.ID, 'password')
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Click the login button
            self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
            
            # Wait for the homepage to load
            try:
                self.wait.until(EC.presence_of_element_located((By.ID, 'global-nav')))
                logger.info("Successfully logged in")
                self.logged_in = True
                
                # Take screenshot after login
                if self.debug:
                    self.driver.save_screenshot(f'debug/{self.session_id}_after_login.png')
                
                # Wait a bit after login
                time.sleep(5)
                
            except TimeoutException:
                # Check if we got a security verification page
                if "security verification" in self.driver.page_source.lower() or "challenge" in self.driver.page_source.lower():
                    logger.warning("Security verification detected. Please complete it manually.")
                    if self.debug:
                        self.driver.save_screenshot(f'debug/{self.session_id}_security_verification.png')
                    input("Complete the security verification and press Enter to continue...")
                    self.logged_in = True
                else:
                    logger.error("Login failed - couldn't detect navigation bar")
                    if self.debug:
                        self.driver.save_screenshot(f'debug/{self.session_id}_login_failure.png')
        
        except Exception as e:
            logger.error(f"Failed to login: {str(e)}")
            if self.debug:
                self.driver.save_screenshot(f'debug/{self.session_id}_login_error.png')
            raise e
    
    def navigate_to_profile(self, profile_url):
        """Navigate to a LinkedIn profile and ensure it's loaded."""
        if not self.logged_in:
            self.login()
        
        try:
            # Ensure URL is the recent-activity/all page
            if "recent-activity/all" not in profile_url:
                if not profile_url.endswith('/'):
                    profile_url = profile_url + '/'
                profile_url = profile_url + "recent-activity/all/"
            
            logger.info(f"Navigating to activity page: {profile_url}")
            self.driver.get(profile_url)
            
            # Wait for page to load
            time.sleep(5)
            
            # Take screenshot of profile page
            if self.debug:
                self.driver.save_screenshot(f'debug/{self.session_id}_profile_page.png')
            
            # Check if we're on the right page
            if "recent-activity" not in self.driver.current_url:
                logger.warning(f"Not on activity page. Current URL: {self.driver.current_url}")
                
                # Try the alternative posts URL
                base_url = profile_url.replace("recent-activity/all/", "").rstrip('/')
                fallback_url = base_url + "/posts/?feedView=all"
                logger.info(f"Trying fallback URL: {fallback_url}")
                
                self.driver.get(fallback_url)
                time.sleep(5)
                
                if self.debug:
                    self.driver.save_screenshot(f'debug/{self.session_id}_fallback_page.png')
                
                # Check if fallback worked
                if "posts" not in self.driver.current_url and "recent-activity" not in self.driver.current_url:
                    logger.warning(f"Both URLs failed. Current URL: {self.driver.current_url}")
                    return False
            
            # Wait for content to load
            try:
                # Wait for any of these elements that indicate posts are loaded
                selectors = [
                    ".occludable-update",
                    ".feed-shared-update-v2",
                    ".profile-creator-shared-feed-update__container"
                ]
                
                for selector in selectors:
                    try:
                        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                        logger.info(f"Found posts with selector: {selector}")
                        return True
                    except:
                        continue
                
                logger.warning("Could not find any post elements")
                if self.debug:
                    self.driver.save_screenshot(f'debug/{self.session_id}_no_posts_found.png')
                return False
                
            except TimeoutException:
                logger.warning("Timeout waiting for posts to load")
                if self.debug:
                    self.driver.save_screenshot(f'debug/{self.session_id}_posts_timeout.png')
                return False
                
        except Exception as e:
            logger.error(f"Error navigating to profile: {str(e)}")
            if self.debug:
                self.driver.save_screenshot(f'debug/{self.session_id}_navigation_error.png')
            return False
    def scroll_to_top(self):
        """Scroll to the top of the page."""
        try:
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            logger.info("Scrolled to top of page")
            return True
        except Exception as e:
            logger.error(f"Error scrolling to top: {str(e)}")
            return False
    def check_for_redirect(self, original_url):
        """Check if LinkedIn has redirected us to a different page."""
        try:
            current_url = self.driver.current_url
            
            # Extract the core profile identifier from both URLs
            def extract_profile_id(url):
                if '/in/' in url:
                    # Extract profile slug from URL like /in/profile-name/
                    profile_part = url.split('/in/')[1].split('/')[0]
                    return profile_part
                elif '/company/' in url:
                    # Extract company slug from URL like /company/company-name/
                    profile_part = url.split('/company/')[1].split('/')[0]
                    return profile_part
                return None
            
            original_profile = extract_profile_id(original_url)
            current_profile = extract_profile_id(current_url)
            
            # Check if we're still on the same profile
            if original_profile and current_profile:
                if original_profile != current_profile:
                    logger.warning(f"Profile redirect detected: {original_profile} -> {current_profile}")
                    return True
            
            # IMPORTANT FIX: Don't treat individual post URLs as redirects
            # These are normal when "see more" buttons are clicked
            if '/feed/update/urn:li:activity:' in current_url:
                logger.info("On individual post page - this is normal behavior, navigating back")
                # Navigate back to the posts page and continue
                try:
                    # Try to go back to the posts page
                    if '/company/' in original_url:
                        # For company pages
                        base_url = original_url.split('/posts/')[0] if '/posts/' in original_url else original_url.split('/recent-activity/')[0]
                        posts_url = base_url.rstrip('/') + '/posts/?feedView=all'
                    else:
                        # For individual profiles
                        base_url = original_url.split('/recent-activity/')[0] if '/recent-activity/' in original_url else original_url.split('/posts/')[0]
                        posts_url = base_url.rstrip('/') + '/recent-activity/all/'
                    
                    logger.info(f"Navigating back to posts page: {posts_url}")
                    self.driver.get(posts_url)
                    time.sleep(3)  # Give time to load
                    
                    # Scroll back to where we were (roughly)
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                    time.sleep(2)
                    
                    return False  # Not a real redirect, we handled it
                except Exception as e:
                    logger.error(f"Error navigating back from individual post: {str(e)}")
                    return False  # Continue anyway
            
            # Check for valid posts pages (either recent-activity or posts/?feedView=all)
            valid_posts_patterns = [
                'recent-activity',
                'posts/?feedView=all',
                'posts?feedView=all'
            ]
            
            is_on_valid_posts_page = any(pattern in current_url for pattern in valid_posts_patterns)
            
            # If we're on a valid posts page for the same profile, it's not a redirect
            if is_on_valid_posts_page and original_profile and current_profile and original_profile == current_profile:
                return False
            
            # Check for actual problematic redirects (not individual posts)
            redirect_indicators = [
                '/feed/' if '/feed/update/' not in current_url else None,  # Exclude individual posts
                '/search/',
                '/checkpoint/',
                '/uas/login',
                '/authwall',
                '/login',
                'linkedin.com/404',
                'linkedin.com/error'
            ]
            
            # Remove None values
            redirect_indicators = [x for x in redirect_indicators if x is not None]
            
            for indicator in redirect_indicators:
                if indicator in current_url.lower():
                    logger.warning(f"LinkedIn redirect detected to: {current_url}")
                    return True
            
            # Check if we're no longer on a posts page when we should be (but allow individual posts)
            if not is_on_valid_posts_page and '/feed/update/' not in current_url:
                # But allow company pages since they might load differently
                if '/company/' not in current_url and '/in/' not in current_url:
                    logger.warning(f"Redirected away from posts page: {current_url}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for redirect: {str(e)}")
            return False
    
    def scroll_and_extract_incrementally(self, category, original_url, max_scrolls=10, profile_name_override=None):
        """Scroll the page and extract posts incrementally. Stop if redirected but keep accumulated posts."""
        try:
            # First scroll to top
            self.scroll_to_top()
            
            # Take screenshot before scrolling
            if self.debug:
                self.driver.save_screenshot(f'debug/{self.session_id}_before_scrolling.png')
            
            posts_loaded = set()  # Track unique posts to avoid counting duplicates
            self.accumulated_posts = []  # Reset accumulated posts for this profile
            processed_texts = set()  # Track processed posts to avoid duplicates
            
            # Get profile name - use override if provided
            if profile_name_override:
                profile_name = profile_name_override
                logger.info(f"Using profile name override: {profile_name}")
            else:
                profile_name = self.extract_profile_name()
                logger.info(f"Extracted profile name: {profile_name}")
            
            # Scroll down gradually to load posts
            for i in range(max_scrolls):
                logger.info(f"Scroll {i+1}/{max_scrolls}")
                
                # Check for redirect before continuing
                if self.check_for_redirect(original_url):
                    logger.warning(f"Redirect detected during scroll {i+1}")
                    logger.info(f"Saving {len(self.accumulated_posts)} posts collected so far")
                    if self.debug:
                        self.driver.save_screenshot(f'debug/{self.session_id}_redirect_detected.png')
                    return self.accumulated_posts  # Return what we have so far
                
                # Find all "see more" links and expand them
                self.expand_all_see_more()
                
                # Extract posts from current view
                current_batch_posts = self.extract_current_posts(category, profile_name, processed_texts)
                
                # Add new posts to accumulated posts
                new_posts_count = 0
                for post in current_batch_posts:
                    if post['post_text'] not in processed_texts:
                        self.accumulated_posts.append(post)
                        processed_texts.add(post['post_text'])
                        new_posts_count += 1
                
                logger.info(f"Found {new_posts_count} new posts. Total accumulated: {len(self.accumulated_posts)}")
                
                # If we have enough posts, we can stop scrolling
                if len(self.accumulated_posts) >= self.max_posts:
                    logger.info(f"Reached target of {self.max_posts} posts")
                    break
                
                # Scroll down more aggressively for more posts
                self.driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(3)
                
                # Check for redirect after scrolling
                if self.check_for_redirect(original_url):
                    logger.warning(f"Redirect detected after scroll {i+1}")
                    logger.info(f"Saving {len(self.accumulated_posts)} posts collected so far")
                    if self.debug:
                        self.driver.save_screenshot(f'debug/{self.session_id}_redirect_after_scroll.png')
                    return self.accumulated_posts  # Return what we have so far
                
                # Every 3 scrolls, take a screenshot and check URL
                if self.debug and i % 3 == 0:
                    self.driver.save_screenshot(f'debug/{self.session_id}_scrolling_{i+1}.png')
            
            # Final expansion of "see more" links
            self.expand_all_see_more()
            
            # Final redirect check
            if self.check_for_redirect(original_url):
                logger.warning("Redirect detected during final expansion")
                logger.info(f"Saving {len(self.accumulated_posts)} posts collected so far")
                return self.accumulated_posts
            
            # Final extraction
            final_batch_posts = self.extract_current_posts(category, profile_name, processed_texts)
            for post in final_batch_posts:
                if post['post_text'] not in processed_texts:
                    self.accumulated_posts.append(post)
                    processed_texts.add(post['post_text'])
            
            # Take screenshot after scrolling
            if self.debug:
                self.driver.save_screenshot(f'debug/{self.session_id}_after_scrolling.png')
            
            logger.info(f"Successfully completed scraping. Total posts: {len(self.accumulated_posts)}")
            return self.accumulated_posts
            
        except Exception as e:
            logger.error(f"Error during scrolling: {str(e)}")
            if self.debug:
                self.driver.save_screenshot(f'debug/{self.session_id}_scrolling_error.png')
            # Even on error, return what we have accumulated
            logger.info(f"Returning {len(self.accumulated_posts)} posts despite error")
            return self.accumulated_posts
    
    def extract_current_posts(self, category, profile_name, processed_texts):
        """Extract posts currently visible on the page."""
        try:
            # Find all post containers
            post_selectors = [
                ".feed-shared-update-v2",
                ".occludable-update",
                ".profile-creator-shared-feed-update__container"
            ]
            
            all_posts = []
            for selector in post_selectors:
                posts = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if posts:
                    all_posts = posts
                    break
            
            if not all_posts:
                return []
            
            # Extract data from each post
            post_data = []
            
            for i, post in enumerate(all_posts):
                try:
                    # Check if this is an original post
                    if not self.is_original_post(post):
                        continue
                    
                    # Extract post data
                    post_text = self.extract_post_text(post)
                    
                    # Skip if we've already processed this text or it's too short
                    if post_text in processed_texts or len(post_text.strip()) < 10:
                        continue
                    
                    # Add to post data
                    post_data.append({
                        'profile_name': profile_name,
                        'post_text': post_text,
                        'category': category
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing post {i+1}: {str(e)}")
                    continue
            
            return post_data
            
        except Exception as e:
            logger.error(f"Error extracting current posts: {str(e)}")
            return []
    
    def count_loaded_posts(self):
        """Count the number of posts currently loaded on the page."""
        try:
            post_selectors = [
                ".feed-shared-update-v2",
                ".occludable-update",
                ".profile-creator-shared-feed-update__container"
            ]
            
            max_count = 0
            for selector in post_selectors:
                posts = self.driver.find_elements(By.CSS_SELECTOR, selector)
                max_count = max(max_count, len(posts))
            
            return max_count
        except:
            return 0
    
    def expand_all_see_more(self):
        """Find and click all 'see more' links on the page."""
        try:
            # Find all elements that might be "see more" buttons
            see_more_selectors = [
                ".inline-show-more-text__button",
                ".feed-shared-inline-show-more-text__see-more",
                ".feed-shared-text-view__see-more",
                ".see-more",
                "span.lt-line-clamp__more"
            ]
            
            for selector in see_more_selectors:
                try:
                    see_more_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Found {len(see_more_buttons)} potential 'see more' buttons with selector: {selector}")
                    
                    for button in see_more_buttons:
                        try:
                            if button.is_displayed():
                                # Try to scroll to the button
                                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                                time.sleep(1)
                                
                                # Try JavaScript click
                                try:
                                    self.driver.execute_script("arguments[0].click();", button)
                                    logger.info("Expanded post with JS click")
                                    time.sleep(1)
                                except:
                                    # Try regular click
                                    try:
                                        button.click()
                                        logger.info("Expanded post with regular click")
                                        time.sleep(1)
                                    except:
                                        pass
                        except:
                            continue
                except:
                    continue
            
            # Also try a more aggressive approach with JavaScript
            try:
                expanded_count = self.driver.execute_script("""
                    const expandButtons = [];
                    
                    // Find all elements containing "...more" or "see more" text
                    const allElements = document.querySelectorAll('*');
                    for (const el of allElements) {
                        const text = el.textContent;
                        if ((text.includes('…more') || 
                             text.includes('...more') || 
                             text.toLowerCase().includes('see more')) && 
                            el.offsetWidth > 0 && 
                            el.offsetHeight > 0) {
                            
                            try {
                                el.click();
                                expandButtons.push(el);
                            } catch (e) {
                                // Try parent element
                                try {
                                    el.parentElement.click();
                                    expandButtons.push(el.parentElement);
                                } catch (e2) {
                                    // Ignore
                                }
                            }
                        }
                    }
                    
                    return expandButtons.length;
                """)
                
                if expanded_count > 0:
                    logger.info(f"Expanded {expanded_count} 'see more' buttons with JavaScript")
                    time.sleep(2)
            except:
                pass
                
            return True
            
        except Exception as e:
            logger.error(f"Error expanding 'see more' links: {str(e)}")
            return False
    
    def extract_posts(self, category, profile_name_override=None):
        """Extract all original posts from the current page. Modified to handle 50 posts."""
        try:
            if self.debug:
                self.driver.save_screenshot(f'debug/{self.session_id}_before_extraction.png')
            
            # First, scroll to top to ensure we start from the top (most recent posts)
            self.scroll_to_top()
            time.sleep(3)  # Give page time to load top content
            
            # Find all post containers - increased limit to get more posts
            post_selectors = [
                ".feed-shared-update-v2",
                ".occludable-update",
                ".profile-creator-shared-feed-update__container"
            ]
            
            all_posts = []
            for selector in post_selectors:
                posts = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if posts:
                    logger.info(f"Found {len(posts)} posts with selector: {selector}")
                    # Increased from 15 to handle more posts, but cap at reasonable number
                    all_posts = posts[:100]  # Take up to 100 posts to filter from
                    break
            
            if not all_posts:
                logger.warning("No posts found")
                if self.debug:
                    self.driver.save_screenshot(f'debug/{self.session_id}_no_posts.png')
                return []
            
            # Extract data from each post
            post_data = []
            post_count = 0
            processed_texts = set()  # Track processed posts to avoid duplicates
            
            # Get profile name - use override if provided
            if profile_name_override:
                profile_name = profile_name_override
                logger.info(f"Using profile name override: {profile_name}")
            else:
                profile_name = self.extract_profile_name()
                logger.info(f"Extracted profile name: {profile_name}")
            
            for i, post in enumerate(all_posts):
                try:
                    # Stop if we've reached our target
                    if post_count >= self.max_posts:
                        logger.info(f"Reached target of {self.max_posts} posts")
                        break
                    
                    logger.info(f"Processing post {i+1}/{len(all_posts)} (extracted: {post_count})")
                    
                    # Scroll to the post to ensure it's in view
                    try:
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", post)
                        time.sleep(1)
                    except:
                        logger.warning(f"Could not scroll to post {i+1}")
                    
                    # Debug screenshot every 10 posts
                    if self.debug and i % 10 == 0:
                        self.driver.save_screenshot(f'debug/{self.session_id}_post_{i+1}.png')
                    
                    # Check if this is an original post
                    if not self.is_original_post(post):
                        logger.info(f"Post {i+1} is not an original post, skipping")
                        continue
                    
                    # Extract post data
                    post_text = self.extract_post_text(post)
                    
                    # Skip if we've already processed this text (duplicate detection)
                    if post_text in processed_texts or len(post_text.strip()) < 10:
                        logger.info(f"Post {i+1} is duplicate or too short, skipping")
                        continue
                    
                    processed_texts.add(post_text)
                    
                    # Log the post data being extracted
                    logger.info(f"Post {i+1}: Text length={len(post_text)}")
                    
                    # Add to post data - only the required fields
                    post_data.append({
                        'profile_name': profile_name,
                        'post_text': post_text,
                        'category': category
                    })
                    
                    logger.info(f"Successfully extracted post {post_count + 1}")
                    
                    # Increment post count
                    post_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing post {i+1}: {str(e)}")
                    continue
            
            logger.info(f"Extracted {len(post_data)} posts")
            return post_data
            
        except Exception as e:
            logger.error(f"Error extracting posts: {str(e)}")
            if self.debug:
                self.driver.save_screenshot(f'debug/{self.session_id}_extraction_error.png')
            return []
    
    def is_original_post(self, post):
        """Check if a post is an original post (not a like, comment, etc.)."""
        try:
            # Check for activity indicators
            activity_texts = [
                "liked", "commented on", "replied", "reposted", 
                "shared", "celebrates", "mentioned in", "follows"
            ]
            
            post_text = post.text.lower()
            
            # If the post contains any activity indicators at the beginning, it's not original
            for activity in activity_texts:
                if post_text.startswith(activity) or f"\n{activity}" in post_text[:50]:
                    return False
            
            # Check for content indicators
            content_selectors = [
                ".feed-shared-update-v2__description",
                ".feed-shared-text",
                ".update-components-text",
                ".feed-shared-text-view",
                ".update-components-update-v2__commentary"
            ]
            
            for selector in content_selectors:
                content_elements = post.find_elements(By.CSS_SELECTOR, selector)
                if content_elements and any(el.text.strip() for el in content_elements):
                    return True
            
            # If we can't determine, assume it's not original
            return False
            
        except Exception as e:
            logger.error(f"Error checking if post is original: {str(e)}")
            return False
    
    def extract_post_text(self, post):
        """Extract the text content of a post."""
        try:
            # Try to expand "see more" links in this post
            self.expand_see_more_in_post(post)
            
            # Try different selectors for post content
            content_selectors = [
                ".feed-shared-update-v2__description",
                ".feed-shared-text",
                ".update-components-text",
                ".feed-shared-text-view"
            ]
            
            post_text = ""
            for selector in content_selectors:
                elements = post.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and len(text) > len(post_text):
                        post_text = text
            
            # If no text found, try JavaScript
            if not post_text:
                post_text = self.driver.execute_script("""
                    const post = arguments[0];
                    
                    // Try to find the main text content
                    const contentElements = post.querySelectorAll('p, span.break-words, div.break-words');
                    let text = '';
                    
                    for (const el of contentElements) {
                        if (el.textContent.trim() && el.offsetWidth > 0 && el.offsetHeight > 0) {
                            text += el.textContent.trim() + '\\n';
                        }
                    }
                    
                    return text.trim();
                """, post)
            
            # Clean up the text
            post_text = re.sub(r'\n\s*\n', '\n\n', post_text)  # Remove extra newlines
            post_text = re.sub(r' +', ' ', post_text)  # Remove extra spaces
            
            return post_text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting post text: {str(e)}")
            return "Error extracting text"
    
    def expand_see_more_in_post(self, post):
        """Expand 'see more' links in a specific post."""
        try:
            # Find all "see more" links in this post
            see_more_selectors = [
                ".inline-show-more-text__button",
                ".feed-shared-inline-show-more-text__see-more",
                ".feed-shared-text-view__see-more",
                ".see-more",
                "span.lt-line-clamp__more"
            ]
            
            for selector in see_more_selectors:
                try:
                    see_more_buttons = post.find_elements(By.CSS_SELECTOR, selector)
                    for button in see_more_buttons:
                        try:
                            if button.is_displayed():
                                # Try JavaScript click
                                self.driver.execute_script("arguments[0].click();", button)
                                time.sleep(1)
                        except:
                            pass
                except:
                    continue
            
            # Also try with JavaScript
            self.driver.execute_script("""
                const post = arguments[0];
                
                // Find all elements containing "...more" or "see more" text
                const allElements = post.querySelectorAll('*');
                for (const el of allElements) {
                    const text = el.textContent;
                    if ((text.includes('…more') || 
                         text.includes('...more') || 
                         text.toLowerCase().includes('see more')) && 
                        el.offsetWidth > 0 && 
                        el.offsetHeight > 0) {
                        
                        try {
                            el.click();
                        } catch (e) {
                            // Try parent element
                            try {
                                el.parentElement.click();
                            } catch (e2) {
                                // Ignore
                            }
                        }
                    }
                }
            """, post)
            
            return True
            
        except Exception as e:
            logger.error(f"Error expanding 'see more' in post: {str(e)}")
            return False
    
    def extract_profile_name(self):
        """Extract the profile name from the current page."""
        try:
            # Try to find the profile name
            profile_name = self.driver.execute_script("""
                // Try to find profile name
                const nameElement = document.querySelector('h1.text-heading-xlarge') || 
                                   document.querySelector('.pv-text-details__left-panel h1');
                return nameElement ? nameElement.textContent.trim() : null;
            """)
            
            if not profile_name:
                # Try to extract from URL
                current_url = self.driver.current_url
                if '/in/' in current_url:
                    profile_name = current_url.split('/in/')[1].split('/')[0].replace('-', ' ').title()
                else:
                    profile_name = "Unknown Profile"
            
            return profile_name
            
        except Exception as e:
            logger.error(f"Error extracting profile name: {str(e)}")
            return "Unknown Profile"
    
    def scrape_profile(self, profile_url, category, profile_name_override=None):
        """Scrape a LinkedIn profile for original posts. Save posts to ChromaDB."""
        try:
            # Navigate to the profile
            if not self.navigate_to_profile(profile_url):
                logger.error(f"Failed to navigate to profile: {profile_url}")
                return []
            original_url = profile_url
            
            # Use the incremental scrolling method that handles redirects
            posts = self.scroll_and_extract_incrementally(category, original_url, profile_name_override=profile_name_override)
            
            # Save posts to ChromaDB immediately, even if we were redirected
            if posts:
                self.save_posts_to_chromadb(posts, category, profile_url)
                logger.info(f"Successfully saved {len(posts)} posts to ChromaDB")
            else:
                logger.warning("No posts were extracted from the profile")
            
            return posts
            
        except Exception as e:
            logger.error(f"Error scraping profile {profile_url}: {str(e)}")
            if self.debug:
                self.driver.save_screenshot(f'debug/{self.session_id}_scrape_profile_error.png')
            
            # Even on error, try to save any accumulated posts
            if hasattr(self, 'accumulated_posts') and self.accumulated_posts:
                logger.info(f"Saving {len(self.accumulated_posts)} posts to ChromaDB despite error")
                self.save_posts_to_chromadb(self.accumulated_posts, category, profile_url)
                return self.accumulated_posts
            
            return []
    
    def save_posts_to_chromadb(self, posts, category, profile_url):
        """Save posts to ChromaDB with embeddings."""
        try:
            if not posts:
                logger.warning("No posts to save")
                return False
            
            logger.info(f"Generating embeddings for {len(posts)} posts...")
            
            # Extract texts for embedding
            post_texts = [post['post_text'] for post in posts]
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(post_texts, show_progress_bar=True)
            
            # Get current count for unique IDs
            try:
                current_count = self.collection.count()
            except:
                current_count = 0
            
            # Prepare data for ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            for i, post in enumerate(posts):
                documents.append(post['post_text'])
                metadatas.append({
                    'profile_name': post['profile_name'],
                    'category': category,
                    'profile_url': profile_url,
                    'scraped_at': datetime.now().isoformat(),
                    'session_id': self.session_id
                })
                ids.append(f"post_{current_count + i}_{self.session_id}")
            
            # Add to ChromaDB
            self.collection.add(
                documents=documents,
                embeddings=embeddings.tolist(),
                ids=ids,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully saved {len(posts)} posts to ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"Error saving posts to ChromaDB: {str(e)}")
            return False
    def query_posts(self, query_text, n_results=5, category_filter=None):
        """Query ChromaDB for similar posts."""
        try:
            # Generate embedding for query
            query_embedding = self.embedding_model.encode([query_text])
            
            # Prepare where clause for filtering
            where_clause = {}
            if category_filter:
                where_clause["category"] = category_filter
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=n_results,
                where=where_clause if where_clause else None
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {str(e)}")
            return None
        
    def scrape_user_profile(self, profile_url, category, profile_name_override=None):
        """
        Main method to be called by app.py with user-provided profile URL and category.
        
        Args:
            profile_url (str): LinkedIn profile URL provided by user
            category (str): Category selected by user
            profile_name_override (str, optional): Override the profile name (useful for user's own posts)
        
        Returns:
            list: List of scraped posts
        """
        try:
            logger.info(f"Starting scrape for profile: {profile_url}, category: {category}")
            if profile_name_override:
                logger.info(f"Using profile name override: {profile_name_override}")
            
            posts = self.scrape_profile(profile_url, category, profile_name_override=profile_name_override)
            logger.info(f"Completed scraping. Total posts saved to ChromaDB: {len(posts)}")
            return posts
        
        except Exception as e:
            logger.error(f"Error in scrape_user_profile: {str(e)}")
            return []
    
    def close(self):
        """Close the browser and clean up."""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                logger.info("Browser closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")

def main():
    """Testing function - not used by app.py."""
    
    # Initialize scraper with ChromaDB
    scraper = LinkedInScraper(headless=False, debug=True, max_posts=50, chroma_db_path="chroma_db")
    
    try:
        # Get user input for testing
        profile_url = input("Enter LinkedIn profile URL: ")
        category = input("Enter category: ")
        
        # Use the main scraping method
        posts = scraper.scrape_user_profile(profile_url, category)
        print(f"Scraped and saved {len(posts)} posts to ChromaDB")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    
    finally:
        # Always close the browser
        scraper.close()
        
if __name__ == "__main__":
    main()
