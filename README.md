# Precariousness!
A familiar Jackbox-like trivia game

## Components

#### Game Server
Hosts the game and keeps track of the game state. Other components communicate with the server via HTTP requests and web sockets.

#### Player Client
Used by players to play the game. Players select questions and buzz by interacting with this client.

|           Player Select Category            |             Player Buzzer              |
|:-------------------------------------------:|:--------------------------------------:|
| <img width="500" alt="clue_select" src="https://user-images.githubusercontent.com/7308112/220995719-e55ea831-b78d-4408-9c0f-8fb4780f74a1.png"> | <img width="500" alt="buzzer" src="https://user-images.githubusercontent.com/7308112/220995771-37fe5f36-a044-4398-9fd0-a83cc404cade.png"> |


#### Host Client
Used by the host to see which player buzzed in and to compare players' verbal responses to the correct response.

|        Host Judges Player Response        |
|:-----------------------------------------:|
| <img width="500" alt="host_clue" src="https://user-images.githubusercontent.com/7308112/220995928-9bb95b8b-cef8-4a28-9a0d-dd3436018c81.png"> |

#### Gameboard
Intended to be displayed on a monitor or a TV for the host and players to see. Not interactable. This client displays the game grid and clues.

|             Gameboard Display Tiles             |             Gameboard Display Clue             |
|:-----------------------------------------------:|:----------------------------------------------:|
| <img width="500" alt="gameboard_tiles" src="https://user-images.githubusercontent.com/7308112/220995996-7ce1d836-033e-472d-ac5f-5841ae785211.png"> | <img width="500" alt="gameboard_clue" src="https://user-images.githubusercontent.com/7308112/220996089-e1837cf9-2186-47c4-a195-668fc0472746.png"> |

## Development
- Requires Python 3.11
- Install the dev dependencies: `pip install -r requirements/dev.txt`

## Running Locally

The data for a game is provided to the server via a JSON file that adheres to the [JSON Schema](https://json-schema.org/) located at [server/game_schema.json](server/game_schema.json).

A (fairly) minimal example of a game file:
```json
{
  "rounds": [
    [
      {
        "name": "Look Up",
        "tiles": {
          "100": {
            "clue": "This is the color of the sky",
            "correct_response": "What is blue"
          },
          "200": {
            "clue": "All of the planets in our solar system revolve around this celestial body",
            "correct_response": "What is the sun"
          }
        }
      },
      {
        "name": "Recent History",
        "tiles": {
          "100": {
            "clue": "This man served as President of the United States from 2008 to 2016",
            "correct_response": "Who is Barrack Obama"
          },
          "200": {
            "clue": "This basketball team won the 2019 NBA championship",
            "correct_response": "Who are the Toronto Raptors"
          }
        }
      }
    ]
  ]
}
```

The game server expects to receive a path to a game file via an environment variable called `GAME_FILE` 

To run the server:
```shell
cd path/to/repository_root
GAME_FILE=path/to/my_game_file.json uvicorn server.main:app --host 0.0.0.0
```

With the server now running, clients can connect to the appropriate endpoints using a web browser.
- Players connect to `http://<server_ip_address>:8000/player`
- The host connects to `http://<server_ip_address>:8000/host`
- The gameboard connects to `http://<server_ip_address>:8000/gameboard`
