from mistrs import get_credentials, get_headers, get, post, print_table
from dataclasses import dataclass
import sys

@dataclass
class APIConfig:
    baseurl: str
    headers: dict
    org_id: str
    hooks_url: str

def getorghooks(config: APIConfig):
#Creates Array of pre-existing webhooks
    global mist_api_count
    Hooks_Array = []
    data = get(config.hooks_url, config.headers)
    count = 1
    for i in data:
        hook = {
        "#": count,
        "id" : i.get("id"),
        "name": i.get("name"),
        "url": i.get("url")
        }
        Hooks_Array.append(hook)
        count += 1
    return Hooks_Array

def get_org_id(credentials: dict) -> str:
    org_id = credentials.get("org_id")
    if org_id is None:
        print("\nNo organization ID found in credentials.")
        while True:
            org_id = input("Please enter your organization ID: ").strip()
            if org_id:  # Check if input is not empty
                confirm = input(f"Confirm organization ID '{org_id}' is correct? (y/n): ").lower()
                if confirm == 'y':
                    break
            print("Please enter a valid organization ID")
    return org_id

def userselect(array):
#gets input from user
    print(print_table(array))
    while True:
        try:
            choice = int(input("Enter the number of your choice: "))
            if 1 <= choice <= len(array):
                return array[choice - 1]
            else:
                print("Invalid choice. Please enter a valid number.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def main():
    try:
        # Get credentials and setup
        credentials = get_credentials(otp=True)
        org_id = get_org_id(credentials)
        config = APIConfig(
            baseurl=credentials["api_url"],
            headers=get_headers(credentials["api_token"]),
            org_id=org_id,
            hooks_url=f'{credentials["api_url"]}orgs/{org_id}/webhooks'
        )
        HooksArray = getorghooks(config)
        if len(HooksArray) > 0:
            userselection = userselect(HooksArray)
            hook_id = userselection.get("id")
            ping_hook_url = f'{config.hooks_url}/{hook_id}/ping'
            data = {}
            resp = post(data, ping_hook_url, config.headers)
            if resp:
                print ("Webhook successfully triggered")
        else:
            print("No org level webhooks found")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)

if __name__ == "__main__":
        main()