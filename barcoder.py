from flask import Flask, render_template, request
import requests
import json
# pip install python-telegram-bot
# from telegram import Bot

app = Flask(__name__)

def load_config():
    try:
        with open('config.json', 'r') as config_file:
            config_data = json.load(config_file)
            return config_data
    except FileNotFoundError:
        print("Не найден файл конфигурации 'config.json'.")
        return None

def get_inventory_data(api_url, api_key, inventory_number):
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }

    url = f'{api_url}/hardware/bytag/{inventory_number}'
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        error_json = {
            "status": "error",
            "messages": response.json().get('messages', f"Error: {response.status_code}"),
            "payload": None
        }
        return error_json

def extract_values(data):
    if not data:
        return None, {"status": "error", "messages": "No data received from API", "payload": None}

    if 'status' in data and data['status'] == 'error':
        return None, data
    elif data:
        status_label = data.get('status_label', {}).get('name', '')
        assigned_to_username = ''
        if data.get('assigned_to'):
            assigned_to_username = data.get('assigned_to', {}).get('username', 'Unknown')
        notes = data.get('notes', '')
        model = data.get('model', {}).get('name') or ''
        serial = data.get('serial', '')
        rtd_location_data = data.get('rtd_location', {})
        rtd_location = rtd_location_data.get('name', '') if isinstance(rtd_location_data, dict) else ''

        if data.get('image', '') is not None:
            image = data.get('image', '')
        else:
            image = 'image.png'

        return {
            'status_label': status_label,
            'assigned_to_username': assigned_to_username,
            'notes': notes,
            'model': model,
            'serial': serial,
            'rtd_location': rtd_location,
            'image': image
        }, None
    else:
        return None, None

def send_telegram_message(token, chat_id, thread_id, message):
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    if thread_id:
        params = {'message_thread_id': "f{thread_id}", 'chat_id': f"{chat_id}_{thread_id}", 'text': message}
    else:
        params = {'chat_id': f"{chat_id}", 'text': message}
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"Failed to send message to Telegram. Status code: {response.status_code}")

@app.route('/', methods=['GET', 'POST'])
def index():
    status_label = None
    assigned_to_username = None
    notes = None
    model = None
    serial = None
    rtd_location = None
    error_message = None
    image = ''
    asset_number = ''

    if request.method == 'POST':
        config = load_config()

        if not config:
            error_message = "Ошибка загрузки конфигурации."
        else:
            api_url = config.get('api_url', '')
            api_key = config.get('api_key', '')
            telegram_token = config.get('TELEGRAM_BOT_TOKEN', '')
            telegram_chat_id = config.get('TELEGRAM_CHAT_ID', '')
            thread_id = config.get('thread_id', '')

            inventory_number = request.form.get('inventory_number', '')
            data = get_inventory_data(api_url, api_key, inventory_number)
            asset_number = inventory_number

            values, error = extract_values(data)
            print("Values:", values)

            if values:
                status_label = values['status_label']
                assigned_to_username = values['assigned_to_username']
                notes = values['notes']
                model = values['model']
                serial = values['serial']
                rtd_location = values['rtd_location']
                image = values['image']
                print(f"Поиск {inventory_number} прошел успешно: {assigned_to_username}")
                send_telegram_message(telegram_token, telegram_chat_id, thread_id, f"Поиск {inventory_number} прошел успешно: {values}")
            elif error:
                error_message = error.get('messages', 'Неизвестная ошибка.')
                send_telegram_message(telegram_token, telegram_chat_id, thread_id, f"Ошибка при поиске {inventory_number}: {error_message}")

    return render_template('index.html', status_label=status_label, assigned_to_username=assigned_to_username, 
                           notes=notes, model=model, serial=serial, rtd_location=rtd_location, error_message=error_message, image=image, asset_number=asset_number)

if __name__ == '__main__':
    app.run(debug=True, port=8885, host='0.0.0.0')
