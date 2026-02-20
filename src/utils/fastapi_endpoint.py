import json
from typing import Any, Dict, Union, List, Optional

import httpx

from logging import getLogger

logger = getLogger(__name__)


def sentinelmind_api_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Union[Dict[str, Any], List[Any], str]:
    """
    Makes a GET request to the SentinelMind API.

    Args:
        endpoint (str): The API endpoint to call (e.g., "/status").
        params (Optional[Dict[str, Any]]): Query parameters for the GET request.
        headers (Optional[Dict[str, str]]): Headers for the GET request.
    Returns:
        Union[Dict[str, Any], List[Any], str]: The JSON response from the API or an error message.
    """

    logger.info(
        f"Making GET request to {url} with params: {params} and headers: {headers}"
    )
    try:
        response = httpx.get(
            url,
            params=params,
            headers=headers,
            timeout=10.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text
    except httpx.RequestError as e:
        return f"An error occurred while requesting {e.request.url!r}."
    except httpx.HTTPStatusError as e:
        return f"Error response {e.response.status_code} while requesting {e.request.url!r}."


def sentinelmind_api_post(
    url: str,
    data: Optional[Dict[str, Any]] = None,
    json_data: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Union[Dict[str, Any], List[Any], str]:
    """
    Makes a POST request to the SentinelMind API.

    Args:
        endpoint (str): The API endpoint to call (e.g., "/submit").
        data (Optional[Dict[str, Any]]): Form data for the POST request.
        json_data  Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,: JSON payload for the POST request.
        headers (Optional[Dict[str, str]]): Headers for the POST request.
    Returns:
        Union[Dict[str, Any], List[Any], str]: The JSON response from the API
            or an error message.
    """
    logger.info(
        f"Making POST request to {url} with data: {data}, json: {json_data}, headers: {headers}"
    )
    response = httpx.post(
        url,
        data=data,
        json=json_data,
        headers=headers,
        timeout=100.0,
        follow_redirects=True,
    )
    response_text = response.text

    logger.info(
        f"Response status code: {response.status_code} and response output is : {response_text}"
    )
    if response.status_code != 200:
        logger.error(f"Error response: {response_text}")
        return f"Error response {response.status_code} while requesting {url!r}: {response_text}"

    try:
        json_data = [
            json.loads(line) for line in response_text.strip().splitlines() if line
        ]
        logger.info(f"Decoded JSON data: {json_data}")
        json_response = json_data[-1] if json_data else {}
        logger.info(f"Returning JSON response: {json_response}")
        return json_response
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON response")
        return response_text
