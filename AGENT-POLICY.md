---
ai-generated: 100% - Gemini
---

# Polityka Agentów i Ograniczenia Narzędzi (Denylist Policy)

Niniejsza polityka określa ramy bezpieczeństwa oraz listę zablokowanych narzędzi (denylist) dla agentów operujących w repozytorium projektu `itsm-svcdesk`.

## Uzasadnienie Czarnej Listy Narzędzi
- Bash(rm -rf /): Narzędzie stwarza wysokie ryzyko nieodwracalnego i destrukcyjnego usunięcia kluczowych plików systemowych oraz wolumenów trwale zapisanych danych.
- ComputerUse: Automatyzacja interfejsu graficznego jest całkowicie zbędna w tym projekcie i mogłaby prowadzić do niekontrolowanych modyfikacji środowiska roboczego.
- WebSearch: Ograniczenie stosowane ze względów bezpieczeństwa sieciowego oraz w celu izolacji środowiska wewnątrz lokalnej piaskownicy testowej.