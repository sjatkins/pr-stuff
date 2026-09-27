"""Converters from the Perilous Realms world sources (world/) to JSONL.

The brace-block formats compiled by ``src/tran`` are handled by
:mod:`prworld.tranparse` driven by the schema tables in :mod:`prworld.schemas`
(a transcription of ``src/PRLib/fields.c``). Zone reset scripts have their own
grammar (``src/Zone/parser.y``) in :mod:`prworld.zones`, and the class table
(``world/CLASSES/classes``, read by ``skills.c``) is in :mod:`prworld.classes`.
"""
