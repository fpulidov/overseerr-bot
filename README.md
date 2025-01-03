# Telegram Media Bot

This Telegram bot allows whitelisted users to search for TV shows and movies, view their posters, and request them from a media library. The bot uses the Telegram Bot API and integrates with an external media library API.

## Features

- **Whitelisted Access**: Only users in the whitelist can interact with the bot.
- **Media Search**: Search for TV shows or movies by name.
- **Poster Preview**: View a poster of the selected media.
- **Request Media**: Request movies or specific seasons of TV shows.
- **Conversation Flow**: Handles user interactions using a conversation handler.
- **Error Handling**: Gracefully handles invalid inputs and errors.
- **Logging**: Logs all user actions for debugging and auditing.

## Prerequisites

- Python 3.9+
- A Telegram Bot Token
- Access to a media library API
- Docker (optional, for containerized deployment)

## Environment Variables

The bot relies on a `.env` file for configuration. Below are the expected variables:

| Variable                     | Description                                            |
|------------------------------|--------------------------------------------------------|
| `TELEGRAM_BOT_TOKEN`         | Token for your Telegram bot.                           |
| `MEDIA_LIBRARY_MANAGER_TOKEN`| API key for overseerr.                                 |
| `MERIA_LIBRARY_URL`          | Base URL of the overseerr API service.                 |
| `WHITELISTED_USERS`          | Comma-separated list of whitelisted Telegram user IDs. |

### Example `.env` File
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
MEDIA_LIBRARY_MANAGER_TOKEN=your_media_library_api_key
MERIA_LIBRARY_URL=https://example.com
WHITELISTED_USERS=123456789,987654321
```

## Usage

### Running Locally

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/telegram-media-bot.git
   cd telegram-media-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with the required variables.

4. Run the bot:
   ```bash
   python3 bot.py
   ```

### Running with Docker

1. Build the Docker image:
   ```bash
   docker build -t telegram-media-bot .
   ```

2. Run the Docker container:
   ```bash
   docker run --env-file .env telegram-media-bot
   ```

### Logs

Logs are stored in `telegram_bot.log` and include timestamps, user actions, and debug information. Highly recommended to use log rotation since Telegram bot API produces a lot of noise checking bot health.

## Workflow

1. **Start Command**:
   - Users initiate interaction with `/start`.
   - The bot verifies if the user is whitelisted.

2. **Media Search**:
   - Users choose between TV shows or movies.
   - The bot prompts for a search query.

3. **Poster Preview**:
   - The bot displays posters of search results for user confirmation.

4. **Request Media**:
   - For TV shows, users specify seasons to download.
   - For movies, the request is processed immediately.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

For any issues or feature requests, please open an issue in the repository.
