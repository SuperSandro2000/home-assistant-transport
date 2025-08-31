#pylint: disable=duplicate-code
"""Dresden (VVO) transport integration."""
from __future__ import annotations
import logging
import re
from typing import Optional
from datetime import datetime, timedelta

import requests
import voluptuous as vol

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.sensor import PLATFORM_SCHEMA
from .const import (  # pylint: disable=unused-import
    DOMAIN,  # noqa
    SCAN_INTERVAL,  # noqa
    API_ENDPOINT,
    API_MAX_RESULTS,
    CONF_DEPARTURES,
    CONF_DEPARTURES_DIRECTION,
    CONF_DEPARTURES_STOP_ID,
    CONF_DEPARTURES_WALKING_TIME,
    CONF_DEPARTURES_LINE_NAME,
    CONF_DEPARTURES_PLATFORM,
    CONF_TYPE_BUS,
    CONF_TYPE_EXPRESS,
    CONF_TYPE_FERRY,
    CONF_TYPE_REGIONAL,
    CONF_TYPE_SUBURBAN,
    CONF_TYPE_SUBWAY,
    CONF_TYPE_TRAM,
    CONF_DEPARTURES_NAME,
    DEFAULT_ICON,
)
from .departure import Departure

_LOGGER = logging.getLogger(__name__)

TRANSPORT_TYPES_SCHEMA = {
    vol.Optional(CONF_TYPE_SUBURBAN, default=True): bool,
    vol.Optional(CONF_TYPE_SUBWAY, default=True): bool,
    vol.Optional(CONF_TYPE_TRAM, default=True): bool,
    vol.Optional(CONF_TYPE_BUS, default=True): bool,
    vol.Optional(CONF_TYPE_FERRY, default=True): bool,
    vol.Optional(CONF_TYPE_EXPRESS, default=True): bool,
    vol.Optional(CONF_TYPE_REGIONAL, default=True): bool,
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_DEPARTURES): [
            {
                vol.Required(CONF_DEPARTURES_NAME): str,
                vol.Required(CONF_DEPARTURES_STOP_ID): int,
                vol.Optional(CONF_DEPARTURES_DIRECTION): str,
                vol.Optional(CONF_DEPARTURES_LINE_NAME): str,
                vol.Optional(CONF_DEPARTURES_PLATFORM): str,
                vol.Optional(CONF_DEPARTURES_WALKING_TIME, default=1): int,
                **TRANSPORT_TYPES_SCHEMA,
            }
        ]
    }
)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    _: DiscoveryInfoType | None = None,
) -> None:
    """Set up the sensor platform."""
    if CONF_DEPARTURES in config:
        for departure in config[CONF_DEPARTURES]:
            add_entities([TransportSensor(hass, departure)], True)


class TransportSensor(SensorEntity):
    departures: list[Departure] = []

    def __init__(self, hass: HomeAssistant, config: dict) -> None:
        self.hass: HomeAssistant = hass
        self.config: dict = config
        self.stop_id: int = config[CONF_DEPARTURES_STOP_ID]
        self.sensor_name: str | None = config.get(CONF_DEPARTURES_NAME)
        self.direction: str | None = config.get(CONF_DEPARTURES_DIRECTION)
        self.line_name: str | None = config.get(CONF_DEPARTURES_LINE_NAME)
        # Ensure platform is always a string or None to avoid EntityPlatform confusion
        platform_value = config.get(CONF_DEPARTURES_PLATFORM)
        self.platform_stop: str | None = str(platform_value) if platform_value is not None else None
        self.walking_time: int = config.get(CONF_DEPARTURES_WALKING_TIME) or 1
        # we add +1 minute anyway to delete the "just gone" transport

    @property
    def name(self) -> str:
        return self.sensor_name or f"Stop ID: {self.stop_id}"

    @property
    def icon(self) -> str:
        next_departure = self.next_departure()
        if next_departure:
            return next_departure.icon
        return DEFAULT_ICON

    @property
    def unique_id(self) -> str:
        base_id = f"stop_{self.stop_id}_departures"
        if self.line_name and isinstance(self.line_name, str):
            # Clean line name for use in unique_id (remove special characters)
            clean_line = re.sub(r'[^a-zA-Z0-9]', '_', self.line_name)
            base_id += f"_line_{clean_line}"
        if self.direction and isinstance(self.direction, str):
            # Clean direction for use in unique_id (remove special characters and limit length)
            clean_direction = re.sub(r'[^a-zA-Z0-9]', '_', self.direction)[:20]
            base_id += f"_dir_{clean_direction}"
        if self.platform_stop and isinstance(self.platform_stop, str):
            # Clean platform for use in unique_id
            clean_platform = re.sub(r'[^a-zA-Z0-9]', '_', self.platform_stop)
            base_id += f"_plat_{clean_platform}"
        return base_id

    @property
    def state(self) -> str:
        next_departure = self.next_departure()
        if next_departure:
            line_info = f"{next_departure.line_name}"
            direction_info = ""
            if next_departure.direction:
                direction_info = f" to {next_departure.direction}"
            elif next_departure.platform:
                direction_info = f" (Platform {next_departure.platform})"
            
            gap_info = f" in {next_departure.gap} min" if next_departure.gap > 0 else " now"
            return f"Next {line_info}{direction_info}{gap_info}"
        return "N/A"

    @property
    def extra_state_attributes(self):
        attributes = {
            "departures": [departure.to_dict() for departure in self.departures or []]
        }
        
        # Add filter information to attributes (ensure all values are serializable)
        if self.line_name and isinstance(self.line_name, str):
            attributes["filtered_line"] = self.line_name
        if self.direction and isinstance(self.direction, str):
            attributes["filtered_direction"] = self.direction
        if self.platform_stop and isinstance(self.platform_stop, str):
            attributes["filtered_platform"] = self.platform_stop
        
        # Debug: Log attribute types to help identify serialization issues
        _LOGGER.debug(f"Sensor {self.unique_id} attributes: {type(attributes)}")
        for key, value in attributes.items():
            _LOGGER.debug(f"  {key}: {type(value)} = {value}")
            
        return attributes

    def update(self):
        self.departures = self.fetch_departures()

    def fetch_departures(self) -> Optional[list[Departure]]:
        try:
            response = requests.get(
                url=f"{API_ENDPOINT}",
                params={
                    "time": (
                        datetime.now() + timedelta(minutes=self.walking_time)
                    ).isoformat(),
                    "format": "json",
                    "limit": API_MAX_RESULTS,
                    "stopID": self.stop_id,
                    "isarrival": False,
                    "shorttermchanges": True,
                    "mentzonly": False,
                },
                timeout=30,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as ex:
            _LOGGER.warning(f"API error: {ex}")
            return []
        except requests.exceptions.Timeout as ex:
            _LOGGER.warning(f"API timeout: {ex}")
            return []

        _LOGGER.debug(f"OK: departures for {self.stop_id}: {response.text}")

        # parse JSON response
        try:
            departures = response.json().get('Departures')
        except requests.exceptions.InvalidJSONError as ex:
            _LOGGER.error(f"API invalid JSON: {ex}")
            return []

        # convert api data into objects
        unsorted = [Departure.from_dict(departure) for departure in departures]
        
        # apply filters if specified
        filtered_departures = unsorted
        
        if self.line_name:
            filtered_departures = [d for d in filtered_departures if d.line_name == self.line_name]
        
        if self.direction:
            filtered_departures = [d for d in filtered_departures if d.direction and self.direction.lower() in d.direction.lower()]
        
        if self.platform_stop:
            filtered_departures = [d for d in filtered_departures if d.platform == self.platform_stop]
        
        return sorted(filtered_departures, key=lambda d: d.timestamp)

    def next_departure(self):
        if self.departures and isinstance(self.departures, list):
            return self.departures[0]
        return None
