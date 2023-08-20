import requests


def get_access_token(client_id, client_secret):
    url = 'https://useast.api.elasticpath.com/oauth/access_token'
    client_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }

    response = requests.post(url, data=client_data)
    response.raise_for_status()

    token_content = response.json()
    access_token = token_content['access_token']
    expires_in = token_content.get('expires_in', 0)

    return access_token, expires_in


def get_products(access_token):
    url = 'https://useast.api.elasticpath.com/pcm/products'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_product(access_token, product_id):
    url = f'https://useast.api.elasticpath.com/pcm/products/{product_id}'
    headers = {
        'Authorization': f'Bearer {access_token}',
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_cart(access_token, chat_id):
    url = f'https://useast.api.elasticpath.com/v2/carts/{chat_id}'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_cart_products(access_token, chat_id):
    url = f'https://useast.api.elasticpath.com/v2/carts/{chat_id}/items'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def add_product_to_cart(access_token, chat_id, product_id, quantity):
    url = f'https://useast.api.elasticpath.com/v2/carts/{chat_id}/items'
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    product_data = {
        "data": {
            "id": product_id,
            "type": "cart_item",
            "quantity": quantity
        }
    }

    response = requests.post(url, headers=headers, json=product_data)
    response.raise_for_status()

    return response.json()


def remove_product_from_cart(access_token, chat_id, cart_item_id):
    url = f'https://useast.api.elasticpath.com/v2/carts/{chat_id}/items/{cart_item_id}'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_product_image_url(access_token, image_id):
    url = f'https://useast.api.elasticpath.com/v2/files/{image_id}'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()['data']['link']['href']


def add_client_email(access_token, chat_id, email):
    url = 'https://useast.api.elasticpath.com/v2/customers'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    customer_data = {
        'data': {
            'email': email,
            'type': 'customer',
            'name': str(chat_id)
        }
    }

    response = requests.post(url, headers=headers, json=customer_data)
    response.raise_for_status()
    return response.json()
