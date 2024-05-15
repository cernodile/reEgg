# reEgg
A server emulator for Auxbrain's Egg, Inc. mobile game, written in Python, for version 1.12.13.
This project was created for [Reverse Engineering a Mobile App Protobuf API](https://based.quest/reverse-engineering-a-mobile-app-protobuf-api/) blog posts on based.quest.

## DISCLAIMER
The version of game chosen is deliberate to not affect the current live service. The game developer has had a history of having to
deal with cheaters and I do not wish to furthen the problem by attempting to reverse engineer their efforts against cheaters.
The project's scope is to educate people on how to reverse engineer APIs in order for digital preservation and archival of media.
As API servers shut down, many apps are immediately locked out from being useable or get heavily hindered in capabilities to do anything productive.

## Setup
You will need a VPN app on your phone that can overwrite DNS records (such as AdAway), redirect www.auxbrain.com to the server that's hosting the emulator.

## Configuration
You might want to check out `data/` directory and check for any epoch values. I am using 05/05/2024 as the default epoch for scheduling contracts for example.

## Roadmap
- [ ] First contact
  - [ ] Offer a valid backup
  - [x] Respond with valid payload
  - [x] Unlock Pro Permit
- [x] Gift Calendar
- [ ] Private Server API
  - [ ] Break Piggy Bank week after filling
  - [ ] Rename a device ID to a friendly name via API
  - [ ] Self-service dashboard & GUI
- [ ] Periodicals
  - [ ] Contracts
    - [x] Your First Contract
    - [x] Contract Scheduler
    - [ ] Co-op with computer simulations
  - [x] Events
    - [x] Proof of Concept
    - [x] Event Scheduler

