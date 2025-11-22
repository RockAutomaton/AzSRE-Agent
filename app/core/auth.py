from azure.identity import DefaultAzureCredential
from functools import lru_cache


@lru_cache()
def get_credential():
    """
    Returns a singleton Azure Credential.
    In Docker/Production, this uses Managed Identity or Env Vars.
    In Local Dev, this uses Azure CLI credentials.
    """
    return DefaultAzureCredential()

