"""Logica de negocio de molestia.

Passthrough: la unicidad (usuario_id, fecha, zona_id) la cubre el repo
con ON CONFLICT. Si Fase 8 quiere reglas (ej. "una molestia lumbar hoy
dispara senal de descarga"), este es el lugar.
"""
