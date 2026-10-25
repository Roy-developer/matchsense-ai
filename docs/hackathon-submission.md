# Hackathon submission

## Challenge

Transform synthetic, football-realistic events into explainable match
intelligence, narratives and recaps for studio, broadcast or streaming.

* Official rules: https://github.com/microsoft/insidethegamehackathon/blob/main/OFFICIAL%20RULES.md
* Official repository: https://github.com/microsoft/insidethegamehackathon
* Reactor series: https://developer.microsoft.com/en-us/reactor/series/S-1709/
* Innovation Studio: https://innovation-studio.microsoft.com/

## What is submitted

| Requirement | Status |
|---|---|
| Working, newly built project | This repository |
| Public GitHub repository | https://github.com/Roy-developer/matchsense-ai |
| Project pitch and technologies actually used | `README.md` |
| Public demo URL and instructions | Streamlit + FastAPI, `README.md` quick start |
| Public video under two minutes | See `docs/demo-guide.md` |
| Architecture image and screenshots | `docs/architecture.md` + recorded demo |
| English content | Yes |
| No unauthorised footage, music, trademarks or datasets | Yes — fictional teams, synthetic data |

## Technologies actually used

* Python 3.11, Pydantic 2, pytest
* Streamlit — dashboard
* FastAPI + Uvicorn — API contract
* Docker — reproducible container
* Azure OpenAI / Microsoft Foundry — optional narrative provider behind a
  provider abstraction (deterministic template provider used by default)

## Honest positioning

The broad idea — replaying synthetic football data and narrating it — is not
unique, and this submission does not claim to be first. The defensible
difference is the verification loop: an interpretation is treated as a proposal,
a deterministic Critic challenges it, and only claims whose numbers and event
references check out are published. The dashboard demonstrates this by showing
claims being rejected.

## Limitations to state

* Synthetic, fictional data only — not official Premier League data.
* Shot-quality and threat values are documented heuristics, not calibrated xG.
* One detector type ships (`control_shift`); others are roadmap.
* Confidence is detector strength, not a probability of football truth.
