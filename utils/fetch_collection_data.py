import requests
# NOTE: collect postman data


class PostmanCollectionFetcher:
    def __init__(self, api_key, forked_uid):
        self.api_key = api_key
        self.forked_uid = forked_uid
        self.headers = {'X-Api-Key': self.api_key}

    def get_collection(self):
        url = f'https://api.getpostman.com/collections/{self.forked_uid}'
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f'error fetching collection {self.forked_uid}: {response.status_code} -{response.text}  ')
            return None