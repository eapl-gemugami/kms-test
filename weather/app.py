import asyncio
import aiohttp
import logging
import os
import time
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass
from collections import defaultdict

from flask import Flask, jsonify
from dotenv import load_dotenv

# Note: Adding `TODO(developer)`` is a personal practice
# I bring from creating Code Samples for GCP.

# Load environment variables
load_dotenv()

# Setup logging
# TODO(developer): Adjust logging configuration as needed
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

NUM_MAX_REQUESTS = 10
DEFAULT_TIME_WINDOW_SECS = 60


@dataclass
class WeatherData:
    """Data class for weather information."""

    # TODO(developer): Add or remove fields as needed
    city: str
    temperature: float
    description: str
    humidity: int
    pressure: float
    wind_speed: float
    country: str
    timestamp: str
    error: Optional[str] = None


class RateLimiter:
    """Simple rate limiter implementation."""

    # Note: Due to time constraints, I took this part from a template.

    def __init__(
        self,
        max_requests: int = NUM_MAX_REQUESTS,
        time_window: int = DEFAULT_TIME_WINDOW_SECS,
    ):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)

    def is_allowed(self, key: str = "default") -> bool:
        """Validate if current request is allowed based on rate limit."""
        now = time.time()

        # Clean old requests
        self.requests[key] = [
            req_time
            for req_time in self.requests[key]
            if now - req_time < self.time_window
        ]

        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True
        return False


class WeatherService:
    """Service to fetch weather data from OpenWeatherMap API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.rate_limiter = RateLimiter(
            max_requests=NUM_MAX_REQUESTS, time_window=DEFAULT_TIME_WINDOW_SECS
        )
        self.timeout = aiohttp.ClientTimeout(total=10)

    async def fetch_weather(
        self, session: aiohttp.ClientSession, city: str
    ) -> WeatherData:
        """Fetch weather data for a specific city."""
        start_time = time.time()

        try:
            # Check rate limit
            if not self.rate_limiter.is_allowed():
                logger.warning(f"Rate limit while feching '{city}'")
                return WeatherData(
                    city=city,
                    temperature=0,
                    description="Rate limit exceeded",
                    humidity=0,
                    pressure=0,
                    wind_speed=0,
                    country="",
                    timestamp=datetime.now().isoformat(),
                    error="Rate limit exceeded",
                )

            params = {"q": city, "appid": self.api_key, "units": "metric"}

            async with session.get(
                self.base_url, params=params, timeout=self.timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    weather_data = WeatherData(
                        city=data["name"],
                        temperature=data["main"]["temp"],
                        description=data["weather"][0]["description"],
                        humidity=data["main"]["humidity"],
                        pressure=data["main"]["pressure"],
                        wind_speed=data["wind"]["speed"],
                        country=data["sys"]["country"],
                        timestamp=datetime.now().isoformat(),
                    )

                    # Log performance metrics
                    duration = time.time() - start_time
                    logger.info(
                        f"Successfully fetched weather for {city} in {duration:.2f}s"
                    )

                    return weather_data
                else:
                    error_msg = f"API returned status {response.status}"
                    logger.error(f"Failed to fetch weather for {city}: {error_msg}")
                    return WeatherData(
                        city=city,
                        temperature=0,
                        description="API Error",
                        humidity=0,
                        pressure=0,
                        wind_speed=0,
                        country="",
                        timestamp=datetime.now().isoformat(),
                        error=error_msg,
                    )

        except asyncio.TimeoutError:
            logger.error(f"Timeout occurred while fetching weather for {city}")
            return WeatherData(
                city=city,
                temperature=0,
                description="Request timeout",
                humidity=0,
                pressure=0,
                wind_speed=0,
                country="",
                timestamp=datetime.now().isoformat(),
                error="Request timeout",
            )
        except Exception as e:
            logger.error(f"Unexpected error fetching weather for {city}: {str(e)}")
            return WeatherData(
                city=city,
                temperature=0,
                description="Service unavailable",
                humidity=0,
                pressure=0,
                wind_speed=0,
                country="",
                timestamp=datetime.now().isoformat(),
                error=str(e),
            )

    async def fetch_cities_list(self, cities: List[str]) -> List[WeatherData]:
        """Fetch weather data for multiple cities concurrently."""
        start_time = time.time()

        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_weather(session, city) for city in cities]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle any exceptions that occurred
            weather_data = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Exception occurred for city {cities[i]}: {str(result)}"
                    )
                    weather_data.append(
                        WeatherData(
                            city=cities[i],
                            temperature=0,
                            description="Service error",
                            humidity=0,
                            pressure=0,
                            wind_speed=0,
                            country="",
                            timestamp=datetime.now().isoformat(),
                            error=str(result),
                        )
                    )
                else:
                    weather_data.append(result)

            total_duration = time.time() - start_time
            logger.info(
                f"Fetched weather for {len(cities)} cities in {total_duration:.2f}s"
            )

            return weather_data


# Initialize weather service
API_KEY = os.getenv("OPENWEATHER_API_KEY", "REPLACE_WITH_YOUR_API_KEY")
weather_service = WeatherService(API_KEY)


@app.route("/")
def index():
    """API endpoint to get weather data."""
    # Here we will fetch the weather data for multiple cities concurrently

    # TODO(developer): Replace with your desired cities, or load this from
    # the user preferences from a database
    cities = ["Mexico City", "San Francisco", "London"]

    try:
        # Create a new event loop for the async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        weather_data = loop.run_until_complete(
            weather_service.fetch_cities_list(cities)
        )
        loop.close()

        # Convert to dict for JSON response
        # TODO: Add units!
        weather_dict = [
            {
                "city": data.city,
                "temperature": data.temperature,
                "description": data.description,
                "humidity": data.humidity,
                "pressure": data.pressure,
                "wind_speed": data.wind_speed,
                "country": data.country,
                "timestamp": data.timestamp,
            }
            for data in weather_data
        ]

        # Return the result as a JSON response
        return jsonify(
            {"status": "success", "data": weather_dict, "records": len(weather_dict)}
        )

    except Exception as e:
        logger.error(f"Error in weather endpoint: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="localhost", port=int(os.environ.get("PORT", 8080)), debug=True)
