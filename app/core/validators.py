"""Validateurs réutilisables pour l'application TopoManager"""
# app/core/validators.py
from typing import Optional
from datetime import date
from fastapi import HTTPException

def validate_enum(value: Optional[str], valid_values: list, field_name: str) -> Optional[str]:
    """
    Valide qu'une valeur est dans une liste prédéfinie
    
    Args:
        value: Valeur à valider
        valid_values: Liste des valeurs acceptées
        field_name: Nom du champ pour le message d'erreur
        
    Returns:
        La valeur validée ou None
        
    Raises:
        HTTPException: Si la valeur n'est pas dans la liste
    """
    if value and value not in valid_values:
        raise HTTPException(
            status_code=422, 
            detail=f"{field_name} invalide. Valeurs acceptées: {', '.join(valid_values)}"
        )
    return value

def validate_date(value: Optional[str], field_name: str) -> Optional[str]:
    """
    Valide le format ISO d'une date (YYYY-MM-DD)
    
    Args:
        value: Chaîne de date à valider
        field_name: Nom du champ pour le message d'erreur
        
    Returns:
        La date validée ou None
        
    Raises:
        HTTPException: Si le format est invalide
    """
    if value:
        try:
            date.fromisoformat(value)
        except ValueError:
            raise HTTPException(
                status_code=422, 
                detail=f"{field_name} doit être au format YYYY-MM-DD"
            )
    return value

def clean_payload(fields: dict) -> dict:
    """
    Nettoie un dictionnaire en supprimant les valeurs None et les chaînes vides
    
    Args:
        fields: Dictionnaire de champs à nettoyer
        
    Returns:
        Dictionnaire nettoyé
    """
    return {
        key: value.strip() if isinstance(value, str) else value
        for key, value in fields.items()
        if value is not None and (not isinstance(value, str) or value.strip())
    }