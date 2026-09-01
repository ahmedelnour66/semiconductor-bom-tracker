"""
Nexar (Octopart) API client — handles OAuth2 auth and batch part lookups.

Docs:
  - Getting started: https://support.nexar.com/support/solutions/articles/101000450648
  - Auth flow:        https://support.nexar.com/support/solutions/articles/101000471994
  - Playground (to explore/verify fields): https://api.nexar.com/graphql/

IMPORTANT: Nexar's GraphQL schema evolves over time. Before relying on this
for real, paste QUERY_TEMPLATE into the Playground (with your token) and
confirm the fields below still match — especially anything under `sellers`,
which is the part of the schema most likely to have shifted since this was
written.
"""

import os
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

TOKEN_URL = "https://identity.nexar.com/connect/token"
GRAPHQL_URL = "https://api.nexar.com/graphql"

CLIENT_ID = os.getenv("NEXAR_CLIENT_ID")
CLIENT_SECRET = os.getenv("NEXAR_CLIENT_SECRET")

# supMultiMatch: exact-MPN batch lookup. Verify this in the Playground first.
QUERY_TEMPLATE = """
query MultiMatch($queries: [SupPartMatchQuery!]!) {
  supMultiMatch(queries: $queries) {
    hits
    parts {
      id
      name
      mpn
      manufacturer { name }
      specs {
        attribute { name }
        value
        displayValue
      }
      sellers {
        company { name }
        offers {
          inventoryLevel
          moq
          packaging
          factoryLeadDays
          prices {
            quantity
            price
            currency
          }
        }
      }
    }
  }
}
"""


class NexarClient:
    def __init__(self):
        if not CLIENT_ID or not CLIENT_SECRET:
            raise RuntimeError(
                "Missing NEXAR_CLIENT_ID / NEXAR_CLIENT_SECRET.\n"
                "Copy .env.example to .env and fill in credentials from "
                "your Nexar app at https://portal.nexar.com"
            )
        self._token: Optional[str] = None
        self._client = httpx.Client(timeout=30)

    def _get_token(self) -> str:
        if self._token:
            return self._token
        resp = self._client.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def lookup_mpns(self, mpns: list[str]) -> dict:
        """Look up a batch of manufacturer part numbers. Returns raw Nexar JSON
        under the `supMultiMatch` key: {"hits": int, "parts": [...]}."""
        token = self._get_token()
        queries = [{"mpn": mpn} for mpn in mpns]
        resp = self._client.post(
            GRAPHQL_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"query": QUERY_TEMPLATE, "variables": {"queries": queries}},
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RuntimeError(f"Nexar API error: {data['errors']}")
        return data["data"]["supMultiMatch"]
