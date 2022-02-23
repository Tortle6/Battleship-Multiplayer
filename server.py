import socket
import pickle
import time
import threading
from dataclasses import dataclass, field

empty = "—"
COST = {"torpedo": 1000, "bomb": 750}

HEADERSIZE = 10

IP = "192.168.1.12"
PORT = 1234

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server_socket.bind((IP, PORT))
server_socket.listen(2)

clients = []

turn = "client1"

# Classes


@dataclass
class Client:
    """ Client class """
    money: int
    guess_board: list
    board: list = None
    client_socket: socket.socket = None


client1 = Client(money=350, guess_board=[[empty for _ in range(10)] for _ in range(10)])
client2 = Client(money=350, guess_board=[[empty for _ in range(10)] for _ in range(10)])


@dataclass
class Ship:
    """ Client ship class """
    name: str
    length: int
    sunk: False
    coords: list[tuple] = field(default_factory=list)


client1ships = [
    Ship(name="Aircraft Carrier", length=5, sunk=False),
    Ship(name="Battleship", length=4, sunk=False),
    Ship(name="Submarine", length=3, sunk=False),
    Ship(name="Cruiser", length=3, sunk=False),
    Ship(name="Destroyer", length=2, sunk=False)
]

client2ships = [
    Ship(name="Aircraft Carrier", length=5, sunk=False),
    Ship(name="Battleship", length=4, sunk=False),
    Ship(name="Submarine", length=3, sunk=False),
    Ship(name="Cruiser", length=3, sunk=False),
    Ship(name="Destroyer", length=2, sunk=False)
]


class Powerup:
    def __init__(self, powerup, client_class, opponent, client_move, client_ships):
        self.powerup = powerup
        self.client_class = client_class
        self.opponent = opponent
        self.client_move = client_move
        self.client_ships = client_ships

    def use_powerup(self):
        if self.powerup == "torpedo":
            self.torpedo()

        elif self.powerup == "bomb":
            self.bomb()

    def torpedo(self):
        self.client_class.money -= COST[self.powerup]

        for y in range(len(self.opponent.board)):
            # If it is a hit

            condition1 = self.opponent.board[y][self.client_move[0]] == "x"
            condition2 = self.client_class.guess_board[y][self.client_move[0]] == empty

            if condition1 and condition2:
                self.client_class.guess_board, self.client_ships, self.client_class.money = make_hit(self.client_class, (self.client_move[0], y), self.client_ships)
                break

            # Else, mark as a miss
            elif not condition1 and condition2:
                self.client_class.guess_board[y][self.client_move[0]] = "o"

        return self.client_ships, self.client_class.guess_board, self.client_class.money

    def bomb(self):
        self.client_class.money -= COST[self.powerup]

        # Iterate through the y direction
        for y in range(self.client_move[1] - 1, self.client_move[1] + 2):
            condition1 = self.opponent.board[y][self.client_move[0]] == "x"
            condition2 = self.client_class.guess_board[y][self.client_move[0]]

            if y >= len(self.client_class.guess_board):
                break

            # If it is a hit
            elif condition1 and condition2:
                self.client_class.guess_board, self.client_ships, self.client_class.money = make_hit(self.client_class, (self.client_move[0], y), self.client_ships)

            elif not condition1 and condition2:
                self.client_class.guess_board[y][self.client_move[0]] = "o"

        # Iterate through the x direction
        for x in range(self.client_move[0] - 1, self.client_move[0] + 2):
            condition1 = self.opponent.board[self.client_move[1]][x] == "x"
            condition2 = self.client_class.guess_board[self.client_move[1]][x] == empty

            if x >= len(self.client_class.guess_board):
                break

            # If it is a hit

            elif condition1 and condition2:
                self.client_class.guess_board, self.client_ships, self.client_class.money = make_hit(self.client_class, (x, self.client_move[1]), self.client_ships)

            elif not condition1 and condition2:
                self.client_class.guess_board[self.client_move[1]][x] = "o"

        return self.client_ships, self.client_class.guess_board, self.client_class.money


# Functions


def recieve(client_socket, pickled):  # Recieve a message
    try:
        message_header = client_socket.recv(HEADERSIZE)
        message_length = int(message_header.decode('utf-8').strip())

        if pickled:  # If the message was pickled
            message = client_socket.recv(message_length)
            message = pickle.loads(message)

        else:
            message = client_socket.recv(message_length).decode("utf-8")

        return message
    except ConnectionResetError:
        clients.remove(client_socket)
        print("Client disconnected.")


def send(client_socket, message, pickled):
    print(f"Sent {message} to {client_socket}. Pickled: {pickled}")
    message = pickle.dumps(message) if pickled else message.encode("utf-8")
    message = f"{len(message):<{HEADERSIZE}}".encode("utf-8") + message

    try:
        client_socket.send(message)

    except ConnectionResetError:
        clients.remove(client_socket)
        print("Client disconnected.")


def manage_clients():  # Handle clients connecting and disconnecting
    while True:
        clientsocket, address = server_socket.accept()

        # Accepts only 2 clients
        if len(clients) > 1:
            print(f"{address} tried to connect but the socket was closed by the server.")
            clientsocket.close()

        else:
            clients.append(clientsocket)
            print(f"{address} connected. {len(clients)}/2 connected.")


def check_hit(x, y, current_board):  # Check if the cilent hit or miss.
    return "hit" if current_board[y][x] == "x" else "miss"


def win_check(current_board, guess_board):  # Check if the client won
    for i in range(len(current_board)):
        for x in range(len(current_board)):
            if guess_board[i][x] == empty and current_board[i][x] == "x":
                return False
    return True


def turns(client_class, opponent, client_ships):
    # Notify the client it is their turn
    send(client_class.client_socket, opponent.guess_board, True)

    # Recieve the client's powerup
    powerup = recieve(pickled=True, client_socket=client_class.client_socket)

    # Recieve the client's move
    move = recieve(pickled=True, client_socket=client_class.client_socket)

    # Update the board
    if powerup == "":
        client_class.guess_board[move[1]][move[0]] = "x" if opponent.board[move[1]][move[0]] == "x" else "o"
        remove_ship(client_ships, move)

    else:
        p = Powerup(powerup, client_class, opponent, move, client_ships)
        p.use_powerup()

    # Check if player sunk a ship

    result, client_ships = if_sank(client_ships)
    send(client_class.client_socket, result, True)

    if result:
        client_class.money += 250

    # Check if the cient's move is a hit and send the result back
    hit = check_hit(move[0], move[1], opponent.board)

    send(client_class.client_socket, hit, False)
    if hit == "hit" and powerup == "":
        client_class.money += 150

    # Send money to client
    send(client_class.client_socket, client_class.money, True)

    # Return if client won
    win = win_check(opponent.board, client_class.guess_board)

    for client_socket in clients:
        send(client_socket, win, True)

    # If the client won, send each other's ship placements
    if win:
        # Send to client socket
        send(client_class.client_socket, opponent.board, True)

        # Send to opponent client socket
        send(opponent.client_socket, client_class.board, True)

    # Send guess board to client
    else:
        send(client_socket=client_class.client_socket, message=client_class.guess_board, pickled=True)

    return client_class.guess_board, client_ships, client_class.money


def remove_ship(ships, coords):  # Removes ship from ship class
    for client_ship in ships:
        for coord in client_ship.coords:
            if coord == coords:
                client_ship.coords.remove(coords)
    return ships


def if_sank(ships):  # Checks if the user sank a ship
    for client_ship in ships:
        if len(client_ship.coords) == 0 and not client_ship.sunk:
            client_ship.sunk = True
            return client_ship.name, ships
    return False, ships


def make_hit(client_class, client_move, client_ships):
    client_class.guess_board[client_move[1]][client_move[0]] = "x"
    client_ships = remove_ship(client_ships, (client_move[0], client_move[1]))
    client_class.money += 150
    return client_class.guess_board, client_ships, client_class.money


if __name__ == "__main__":
    t = threading.Thread(target=manage_clients)
    t.start()

    # Wait for players to connect

    print("Waiting for players to connect.")
    while len(clients) < 2:
        time.sleep(1)

    while len(clients) >= 2:
        # Notify clients to start the game

        for client in clients:
            send(client_socket=client, message="game start", pickled=True)

        # Send prices
        for client in clients:
            send(client_socket=client, pickled=True, message=COST)

        # Send money
        send(clients[0], client1.money, True)
        send(clients[1], client2.money, True)

        # Recieve the player's battleship placements

        client1.client_socket = clients[0]
        client2.client_socket = clients[1]

        client1.board = recieve(client1.client_socket, True)
        client2.board = recieve(client2.client_socket, True)
        client1_ship_list = recieve(client1.client_socket, True)
        client2_ship_list = recieve(client2.client_socket, True)

        # Input ship coordinates for client 1
        for coordinates in client1_ship_list:
            for ship in client1ships:
                if len(coordinates) == ship.length and not ship.coords:
                    ship.coords = coordinates
                    break

        # Input ship coordiantes for client 2
        for coordinates in client2_ship_list:
            for ship in client2ships:
                if len(coordinates) == ship.length and not ship.coords:
                    ship.coords = coordinates
                    break

        # Send to client 1 if they won (the client is expecting this information)
        send(client1.client_socket, win_check(client1.board, client1.guess_board), True)

        # Main game loop
        while True:
            # Handle client 1's turn
            if turn == "client1":
                turn = "client2"
                client1.guess_board, client1ships, client1.money = turns(client1, client2, client1ships)

                # If the client won, reset game
                if win_check(client2.board, client1.guess_board):
                    turn = "client1"
                    client1.guess_board = [[empty for _ in range(10)] for _ in range(10)]
                    client2.guess_board = [[empty for _ in range(10)] for _ in range(10)]

                    time.sleep(10)
                    break

            elif turn == "client2":
                # Handle client 2's turn
                turn = "client1"
                client2.guess_board, client2ships, client2.money = turns(client2, client1, client2ships)

                # If the client won, reset game
                if win_check(client1.board, client2.guess_board):
                    client1.guess_board = [[empty for _ in range(10)] for _ in range(10)]
                    client2.guess_board = [[empty for _ in range(10)] for _ in range(10)]

                    time.sleep(10)
                    break
