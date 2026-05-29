import os
from typing import Dict, Optional

import requests

DEFAULT_INVENTORY_API_BASE_URL = os.environ.get('INVENTORY_API_BASE_URL', 'https://bloodlink-backend-bpll.onrender.com')
DEFAULT_ADMIN_EMAIL = os.environ.get('INVENTORY_ADMIN_EMAIL', 'admin@bloodlink.com')
DEFAULT_ADMIN_PASSWORD = os.environ.get('INVENTORY_ADMIN_PASSWORD', 'Admin123!')
AUTH_PATHS = [
    '/api/auth/login',
]
INVENTORY_PATH = '/api/inventory'


class InventoryIntegrationError(Exception):
    pass


def _build_url(base_url: str, path: str) -> str:
    return base_url.rstrip('/') + path


def _extract_token(response_json: dict) -> Optional[str]:
    for key in ['access_token', 'token', 'jwt', 'accessToken']:
        if key in response_json and response_json[key]:
            return response_json[key]

    if isinstance(response_json.get('data'), dict):
        for key in ['access_token', 'token', 'jwt', 'accessToken']:
            if key in response_json['data'] and response_json['data'][key]:
                return response_json['data'][key]

    return None

COMPONENT_CODE_MAP = {
    'PRBC': 'Packed Red Cells',
    'WHOLE_BLOOD': 'Whole Blood',
    'PLASMA': 'Fresh Frozen Plasma',
    'CRYOPRECIPITATE': 'Cryoprecipitate',
    'CRYO_POOR_PLASMA': 'Fresh Frozen Plasma',
    'PLATELETS': 'Platelets Concentrate'
}


def _normalize_component_code(code: str) -> str:
    if not code:
        return code
    normalized = COMPONENT_CODE_MAP.get(code.upper())
    if normalized:
        return normalized
    return code.replace('_', ' ').title()


def authenticate_admin(base_url: str = DEFAULT_INVENTORY_API_BASE_URL,
                       email: str = DEFAULT_ADMIN_EMAIL,
                       password: str = DEFAULT_ADMIN_PASSWORD) -> str:
    last_error = None
    for path in AUTH_PATHS:
        url = _build_url(base_url, path)
        try:
            response = requests.post(
                url,
                json={
                    'email': email,
                    'password': password,
                },
                timeout=10,
            )
        except requests.RequestException as exc:
            last_error = exc
            continue

        if response.status_code != 200:
            last_error = response.text
            continue

        token = _extract_token(response.json())
        if token:
            return token
        last_error = f'Authentication response did not include an access token from {url}.'

    raise InventoryIntegrationError(
        f'Unable to authenticate to inventory backend. Tried endpoints {AUTH_PATHS}. '
        f'Last error: {last_error}'
    )


def fetch_inventory_stock(base_url: str = DEFAULT_INVENTORY_API_BASE_URL,
                          token: Optional[str] = None) -> Dict[str, int]:
    if token is None:
        token = authenticate_admin(base_url=base_url)

    url = _build_url(base_url, INVENTORY_PATH)
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as exc:
        raise InventoryIntegrationError(f'Unable to fetch inventory data: {exc}')

    if response.status_code != 200:
        raise InventoryIntegrationError(
            f'Inventory fetch failed with status code {response.status_code}: {response.text}'
        )

    data = response.json()
    if isinstance(data, dict) and isinstance(data.get('by_blood_type'), dict):
        return {bt: int(count) for bt, count in data['by_blood_type'].items()}

    if isinstance(data, dict) and 'units' in data and isinstance(data['units'], list):
        units = data['units']
    elif isinstance(data, list):
        units = data
    else:
        raise InventoryIntegrationError('Unexpected inventory response format. Expected "by_blood_type" or "units" list.')

    stock: Dict[str, int] = {}
    for unit in units:
        bt = unit.get('blood_type')
        status = unit.get('status')
        if not bt or status != 'AVAILABLE':
            continue
        stock[bt] = stock.get(bt, 0) + 1

    return stock


def fetch_inventory_breakdown(base_url: str = DEFAULT_INVENTORY_API_BASE_URL,
                               token: Optional[str] = None) -> Dict[str, Dict[str, int]]:
    if token is None:
        token = authenticate_admin(base_url=base_url)

    url = _build_url(base_url, INVENTORY_PATH)
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as exc:
        raise InventoryIntegrationError(f'Unable to fetch inventory data: {exc}')

    if response.status_code != 200:
        raise InventoryIntegrationError(
            f'Inventory fetch failed with status code {response.status_code}: {response.text}'
        )

    data = response.json()
    breakdown: Dict[str, Dict[str, int]] = {}

    if isinstance(data, dict) and isinstance(data.get('by_blood_and_component'), dict):
        for key, count in data['by_blood_and_component'].items():
            if not isinstance(key, str) or '_' not in key:
                continue
            blood_type, component_code = key.split('_', 1)
            component_type = _normalize_component_code(component_code)
            if not blood_type:
                continue
            breakdown.setdefault(blood_type, {})[component_type] = int(count)
        return breakdown

    if isinstance(data, dict) and 'units' in data and isinstance(data['units'], list):
        units = data['units']
    elif isinstance(data, list):
        units = data
    else:
        raise InventoryIntegrationError('Unexpected inventory response format. Expected "by_blood_and_component" or "units" list.')

    for unit in units:
        bt = unit.get('blood_type')
        status = unit.get('status')
        component_type_raw = unit.get('component_type')
        if not bt or status != 'AVAILABLE' or not component_type_raw:
            continue
        component_type = _normalize_component_code(component_type_raw)
        breakdown.setdefault(bt, {})[component_type] = breakdown.setdefault(bt, {}).get(component_type, 0) + 1

    return breakdown
