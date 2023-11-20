from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import time
import re
import time
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer


#Natural Language Installer
nltk.download('vader_lexicon')
sia = SentimentIntensityAnalyzer()


class Review:
 def __init__(self, username, review, stars, helpful_count, verified_purchase, profile_link, profile_hearts = -1, profile_following = -1):
     self.username = username
     self.review = review
     self.stars = stars
     self.helpful_count = helpful_count
     self.verified_purchase = verified_purchase
     self.profile_link = profile_link
     self.profile_hearts = profile_hearts
     self.profile_following = profile_following


def analyze_sentiment(review, sia):
   # Analyze sentiment of the review
   sentiment_scores = sia.polarity_scores(review)
   # Calculate an overall rating based on compound score
   overall_rating = (sentiment_scores['compound'] + 1) * 5   # Map compound score to a 1-10 scale


   return overall_rating


def potential_bot(review):
  # Sentiment Analysis (example using VaderSentiment)
  sentiment_score = analyze_sentiment(review.review,sia)
  # Contextual checks
  if (
      sentiment_score < 5 or
       not review.verified_purchase or
       review.helpful_count <= 0
  ):
      return True
  return False


# Set up the webdriver (in this example, using Chrome)
driver = webdriver.Edge()
product_url = 'https://www.amazon.com/Bose-QuietComfort-45-Bluetooth-Canceling-Headphones/dp/B098FH5P3C/ref=asc_df_B098FKXT8L/?tag=hyprod-20&linkCode=df0&hvadid=532264134702&hvpos=&hvnetw=g&hvrand=16876443853742772586&hvpone=&hvptwo=&hvqmt=&hvdev=c&hvdvcmdl=&hvlocint=&hvlocphy=9003964&hvtargid=pla-1414999816226&mcid=3c1ac3317e91305db68b42539ab9e1b9&th=1'
all_reviews = []    # holds all reviews from all pages
num_pages_to_iterate = 15


try:
   # Open the Amazon product page
   driver.get(product_url)
   time.sleep(1)
   reviews_div = driver.find_element(By.ID, "reviews-medley-footer")
   html_text = reviews_div.get_attribute('innerHTML')
   pattern = re.compile(r'href="(.*?)"')


   # Find all matches in the HTML string
   matches = pattern.findall(html_text)


   # Print the extracted href values
   product_review_url = "https://www.amazon.com"
   for match in matches:
       product_review_url = product_review_url + str(match)
   product_review_url += '&pageNumber=1'


   # iterate a certain number of pages or until there we try to access a page that does not exist
   for page_number in range(1, num_pages_to_iterate):
       driver.get(product_review_url)
       time.sleep(1)
       print('Page: ' + str(page_number), product_review_url)
       all_reviews_read = False    # tracks if we have read all reviews on a given page
       curr_page_reviews = set()    # set of current reviews on page to check for duplicates if found this will signify to switch to the next page
       checkProfileList = []


       while not all_reviews_read:
           try:
               WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.review')))
           except NoSuchElementException:
               break


           review_elements = driver.find_elements(By.CSS_SELECTOR, '.review')
           for review_element in review_elements:
               try:
                   username = review_element.find_element(By.CSS_SELECTOR, '.a-profile-name').text
                   review_text = review_element.find_element(By.CSS_SELECTOR, '.review-text').text
                   verified_purchase = 'Verified Purchase' in review_element.text
               except NoSuchElementException:
                   # Handle the exception or log the error
                   print("Failed to retrieve username, review text, or verified purchase status.")
                   continue


               # access profile
               try:
                   profile_element = review_element.find_element(By.CSS_SELECTOR, '.a-profile')
                   profile_href = profile_element.get_attribute('href')
               except NoSuchElementException:
                   # Handle the exception or log the error
                   print("Profile element not found for this review.")
                   profile_href = ''


               try:
                   helpful_count_text = review_element.find_element(By.CSS_SELECTOR, '.cr-vote-text').text.split(' ')[0]
                   helpful_count = int(re.sub(r'\D', '', helpful_count_text))  # Extract digits
               except (NoSuchElementException, ValueError):
                   helpful_count = 0

                
               stars_element = review_element.find_element(By.CSS_SELECTOR, '.a-icon-star .a-icon-alt')
               stars_text = stars_element.get_attribute('innerHTML').split(' ')[0]
               stars = int(float(stars_text.split()[0]))
               current_review = Review(username, review_text, stars, helpful_count, verified_purchase, profile_href)


               # code for seeing if all reviews on the current page have been read
               if current_review.review not in curr_page_reviews:
                   curr_page_reviews.add(current_review.review)
                   if potential_bot(current_review): # if it is a potential bot, add to list scrape profile
                       checkProfileList.append(current_review)  
                     
               print(f"Name: - {username} Stars {str(stars)}")
               all_reviews.append(current_review)
           all_reviews_read = True


       # Navigating back to the product_review_url after the loop completes
       driver.get(product_review_url)
       time.sleep(1)


       # Process to scrape profiles for potential bots
       for review in checkProfileList:
           try:
               driver.get(review.profile_link)
               WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.impact-cell')))
               pf_elements = driver.find_elements(By.CLASS_NAME, 'impact-cell')
               for pf_element in pf_elements:
                   type_of_info = pf_element.text.split('\n')[1].strip().lower()  # Convert to lowercase for case-insensitive comparison
                 
                   if type_of_info == 'hearts':
                       review.profile_hearts = pf_element.text.split('\n')[0]


                   elif type_of_info == 'following':
                       review.profile_following = pf_element.text.split('\n')[0]
           except Exception as e:
               print(f"")


       # Update the product_review_url for the next iteration
       url_pattern = re.compile(r'(pageNumber=\d+)')
       product_review_url = url_pattern.sub(r'pageNumber=' + str(page_number + 1), product_review_url)


except Exception as e:
   print(f"")


finally:
   # Close the browser window
   driver.quit()
   output_file_path = "amazon_reviews_with_profile.txt"
   with open(output_file_path, "w", encoding="utf-8") as output_file:
       for review in all_reviews:
           output_file.write(f"Username: {review.username}\n")
           output_file.write(f"Stars: {review.stars}\n")
           # output_file.write(f"Review: {review.review}\n")
           output_file.write(f"Helpful Count: {review.helpful_count}\n")
           if potential_bot(review):
               output_file.write(f"Account Flagged As A Bot: True\n")
               # Checking if profile hearts and following are available and meet the criteria to classify as a bot
               if review.profile_hearts and review.profile_following:
                   try:
                       profile_hearts = int(review.profile_hearts)
                       profile_following = int(review.profile_following)
                       output_file.write(f'Profile Hearts: {profile_hearts}\n')
                       output_file.write(f'Profile Following: {profile_following}\n')
                       if profile_hearts > 50 or profile_following > 15:
                           output_file.write(f'Bot Review: False\n')
                       else:
                           output_file.write(f'Bot Review: True\n')
                   except ValueError:
                       # Handle the case where profile hearts or following couldn't be converted to integers
                       output_file.write(f'Unable to determine bot status. Hearts/Following data not in proper format.\n')
               else:
                   # Handle the case where profile hearts or following are not available
                   output_file.write(f'Profile hearts or following data not found.\n')
           else:
               output_file.write(f"Account Flagged As A Bot: False\n")
               output_file.write(f"Bot Review: False\n")
     
           output_file.write("\n" + "=" * 1000 + "\n\n")
       print(f"All reviews have been written to {output_file_path}")

