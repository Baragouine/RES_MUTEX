import socket
import threading
import argparse
import time

MAIN_MUTEX = threading.Lock()
RES_MUTEXES = {}

# Create new mutex
def create_new_mutex_if_not_exist(res_id:str):
  MAIN_MUTEX.acquire()

  if not (res_id in RES_MUTEXES):
    RES_MUTEXES[res_id] = [threading.Lock(), []]

  MAIN_MUTEX.release()

# release all mutex
def release_all(client_id):
  MAIN_MUTEX.acquire()

  for k, v in RES_MUTEXES.items():
    RES_MUTEXES[k][0].acquire()
    RES_MUTEXES[k][1] = [id for id in RES_MUTEXES[k][1] if id != client_id]
    RES_MUTEXES[k][0].release()

  MAIN_MUTEX.release()

# read_line from socket
def read_line_from_socket(s):
  msg = b""

  while True:
    f = s.recv(1)
    if not f:
      return None
    if f == b"\n":
      break
    msg += f

  return msg.decode("utf-8")

# Manage client
def handle_client(client_socket, client_id):
  client_socket.sendall((client_id + "\n").encode("utf-8"))
  print("new client:", client_id)

  while True:
    try:
      msg = read_line_from_socket(client_socket)

      if msg is None:
        print("client:", client_id, " is not opened")
        break

      msg = msg.split(" ")

      if len(msg) == 1 and msg[0] == "exit":
        print("client:", client_id, "Exit")
        client_socket.sendall("Ok\n".encode())
        break

      if msg[0] == "lock" or msg[0] == "unlock":
        if len(msg) != 2:
          client_socket.sendall("Error\n".encode())
          print("client:", client_id, "- Error")
          break

        if msg[0] == "lock":
          print("client:", client_id, "lock")
          create_new_mutex_if_not_exist(msg[1])
          RES_MUTEXES[msg[1]][0].acquire()
          RES_MUTEXES[msg[1]][1].append(client_id)
          RES_MUTEXES[msg[1]][0].release()

          end_loop = False
          while not end_loop:
            time.sleep(0.01)
            RES_MUTEXES[msg[1]][0].acquire()
            if RES_MUTEXES[msg[1]][1][0] == client_id:
              end_loop = True
            RES_MUTEXES[msg[1]][0].release()

        else:
          print("client:", client_id, "unlock")
          RES_MUTEXES[msg[1]][0].acquire()
          if RES_MUTEXES[msg[1]][1][0] != client_id:
            raise Exception("client", client_id, "unlock")
          RES_MUTEXES[msg[1]][1] = RES_MUTEXES[msg[1]][1][1:]
          RES_MUTEXES[msg[1]][0].release()

        client_socket.sendall("Ok\n".encode())
      else:
        client_socket.sendall("Error\n".encode())
        print("client:", client_id, "- Error")
        break
    except Exception as e:
      client_socket.sendall("Error\n".encode())
      print("client:", client_id, "- Exception:", str(e))
      break

  release_all(client_id)
  print("client", client_id, "end")


def is_notebook() -> bool:
  try:
    shell = get_ipython().__class__.__name__
    if shell == 'ZMQInteractiveShell':
      return True   # Jupyter notebook or qtconsole
    elif shell == 'TerminalInteractiveShell':
      return False  # Terminal running IPython
    else:
      return False  # Other type (?)
  except NameError:
    return False      # Probably standard Python interpreter


# Parse args if script mode
parser = argparse.ArgumentParser(description='RES_MUTEX_CLIENT')

parser.add_argument('-port_num',type=int,default=5002)

args = None

if is_notebook():
  args = parser.parse_args("")
else:
  args = parser.parse_args()



# Create server socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# bind
server_socket.bind(("localhost", args.port_num))

server_socket.listen(1024)

while True:
  client_socket, client_adress = server_socket.accept()
  client_id = "client_" + str(time.time())

  client_thread = threading.Thread(target=handle_client, args=(client_socket, client_id))
  client_thread.start()

server_socket.close()
