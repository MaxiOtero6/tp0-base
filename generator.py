from sys import argv

SERVER_SERVICE = """
  server:
    container_name: server
    image: server:latest
    entrypoint: python3 /main.py
    environment:
      - PYTHONUNBUFFERED=1
    #   - LOGGING_LEVEL=DEBUG
    networks:
      - testing_net
    volumes:
      - ./server/config.ini:/config.ini
"""

CLIENT_SERVICE = """
  client-service-name:
    container_name: client-container-name
    image: client:latest
    entrypoint: /client
    environment:
      - CLI_ID=id
      - NOMBRE=Santiago Lionel
      - APELLIDO=Lorca
      - DOCUMENTO=30904465
      - NACIMIENTO=1999-03-17
      - NUMERO=7574
    #   - CLI_LOG_LEVEL=DEBUG
    networks:
      - testing_net
    depends_on:
      - server
    volumes:
      - ./client/config.yaml:/config.yaml
      - ./.data:/data:ro
"""

NETWORKS = """
networks:
  testing_net:
    ipam:
      driver: default
      config:
        - subnet: 172.25.125.0/24
"""


def save(file: str, data: str) -> None:
    with open(file, "w") as f:
        f.write(data)


def run(file: str, n_clients: int) -> None:
    data: str = "name: tp0\nservices:\n" + SERVER_SERVICE

    for i in range(n_clients):
        data += CLIENT_SERVICE \
            .replace("client-service-name", f"client{i+1}") \
            .replace("client-container-name", f"client{i+1}") \
            .replace("CLI_ID=id", f"CLI_ID={i+1}")

    data += NETWORKS

    save(file, data)


def main() -> None:
    if len(argv) < 3:
        print("Expected: python3 generator.py <file> <n_clients>")
        exit(1)

    file: str = argv[1]
    n_clients: int = int(argv[2])

    run(file, n_clients)


if __name__ == "__main__":
    main()
