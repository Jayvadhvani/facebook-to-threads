import requests

def main():
    print("=== Facebook Permanent Page Access Token Generator ===")
    
    app_id = input("Enter your Facebook App ID: ").strip()
    app_secret = input("Enter your Facebook App Secret: ").strip()
    short_token = input("Enter the short-lived User Access Token from Graph Explorer: ").strip()
    
    # Step 1: Exchange for Long-Lived User Access Token
    print("\n[1/2] Exchanging short-lived token for long-lived token...")
    url_exchange = "https://graph.facebook.com/v20.0/oauth/access_token"
    params_exchange = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token
    }
    
    try:
        res = requests.get(url_exchange, params=params_exchange)
        res.raise_for_status()
        long_lived_token = res.json().get("access_token")
        print("Success! Generated long-lived User Access Token.")
    except Exception as e:
        print(f"Error exchanging token: {e}")
        if 'res' in locals():
            print(f"Response: {res.text}")
        return

    # Step 2: Fetch Page Access Tokens
    print("\n[2/2] Retrieving permanent Page Access Tokens...")
    url_pages = "https://graph.facebook.com/v20.0/me/accounts"
    params_pages = {
        "access_token": long_lived_token
    }
    
    try:
        res_pages = requests.get(url_pages, params=params_pages)
        res_pages.raise_for_status()
        pages_data = res_pages.json().get("data", [])
        
        if not pages_data:
            print("No pages found. Make sure the user has authorized the app for the target page.")
            return
            
        print("\nAvailable Pages and their permanent tokens:")
        print("=" * 60)
        for page in pages_data:
            print(f"Page Name:  {page.get('name')}")
            print(f"Page ID:    {page.get('id')}")
            print(f"Token:      {page.get('access_token')}")
            print("-" * 60)
        print("\nUse the token of your desired page for FB_PAGE_ACCESS_TOKEN in GitHub secrets.")
        
    except Exception as e:
        print(f"Error fetching pages: {e}")
        if 'res_pages' in locals():
            print(f"Response: {res_pages.text}")

if __name__ == "__main__":
    main()
