# run_scraper.py
from pet911_scraper import Pet911Scraper
import pandas as pd
import os

if __name__ == "__main__":
    # Define the initial URLs for lost and found animals
    # IMPORTANT: Replace these with the actual initial URLs for lost and found
    # animals on pet911.ru that you found by inspecting the website.
    lost_animals_initial_url = "https://pet911.ru/catalog?PetsSearch%5Blatitude%5D=55.45035126520772&PetsSearch%5Blongitude%5D=37.36999511718751&PetsSearch%5BlatTopLeft%5D=56.02292412058638&PetsSearch%5BlngTopLeft%5D=39.47937011718751&PetsSearch%5BlatBotRight%5D=54.86930913144641&PetsSearch%5BlngBotRight%5D=35.26062011718751&zoom=9&PetsSearch%5Banimal%5D=on&PetsSearch%5Banimal%5D=-1&PetsSearch%5Btype%5D=0&PetsSearch%5BdateField%5D=1&PetsSearch%5BdatePeriod%5D=4&PetsSearch%5BshowClosedPets%5D=0&PetsSearch%5BshowClosedPets%5D=1"

    # You would need to determine the correct initial URL for found animals
    # For this example, let's just use the same URL for demonstration, but note this limitation.
    # A real implementation needs the correct 'found' URL.
    found_animals_initial_url = "https://pet911.ru/catalog?PetsSearch%5Blatitude%5D=55.45035126520772&PetsSearch%5Blongitude%5D=37.36999511718751&PetsSearch%5BlatTopLeft%5D=56.02292412058638&PetsSearch%5BlngTopLeft%5D=39.47937011718751&PetsSearch%5BlatBotRight%5D=54.86930913144641&PetsSearch%5BlngBotRight%5D=35.26062011718751&zoom=9&PetsSearch%5Banimal%5D=on&PetsSearch%5Banimal%5D=-1&PetsSearch%5Btype%5D=1&PetsSearch%5BdateField%5D=1&PetsSearch%5BdatePeriod%5D=4&PetsSearch%5BshowClosedPets%5D=0&PetsSearch%5BshowClosedPets%5D=1" # Assuming type=1 is for found


    scraper = Pet911Scraper()

    # Scrape lost animals
    print("\n--- Starting Lost Animals Scrape ---")
    df_lost_pets = scraper.scrape_lost_animals(lost_animals_initial_url, max_pages=10) # Scrape first 10 pages
    if not df_lost_pets.empty:
        output_filename_lost = "pet911_lost_pets_scraped_connector.csv"
        df_lost_pets.to_csv(output_filename_lost, index=False, encoding='utf-8-sig')
        print(f"\nSaved scraped lost pets data to {output_filename_lost}")
    else:
        print("\nNo lost pets data scraped.")

    # Scrape found animals
    print("\n--- Starting Found Animals Scrape ---")
    df_found_pets = scraper.scrape_found_animals(found_animals_initial_url, max_pages=10) # Scrape first 10 pages
    if not df_found_pets.empty:
         output_filename_found = "pet911_found_pets_scraped_connector.csv"
         df_found_pets.to_csv(output_filename_found, index=False, encoding='utf-8-sig')
         print(f"\nSaved scraped found pets data to {output_filename_found}")
    else:
        print("\nNo found pets data scraped.")

    print("\nScraping process finished.")
