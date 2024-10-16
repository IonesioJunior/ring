import os
from pathlib import Path
from typing import List
from syftbox.lib import Client, SyftPermission
from ring_function import ring_function
from types import SimpleNamespace
import json

RING_APP_PATH = Path(os.path.abspath(__file__)).parent


def ring_length(ring_data: SimpleNamespace) -> int:
    return len(ring_data.ring)


def load_json(file: str) -> SimpleNamespace:
    with open(file, "r") as f:
        return SimpleNamespace(**json.load(f))


class RingRunner:
    def __init__(self):
        self.client = Client.load()

        self.my_email: str = self.client.email

        # this is where all the app state goes
        self.ring_pipeline_path: Path = (
            Path(self.client.datasite_path) / "app_pipelines" / "ring"
        )
        # this is where the pending inputs go
        self.running_folder: Path = self.ring_pipeline_path / "running"
        # this is where the final result goes of a completed ring
        self.done_folder: Path = self.ring_pipeline_path / "done"
        # this is your personal secret
        self.secret_file: Path = RING_APP_PATH / "secret.txt"

    def run(self) -> None:
        self.setup_folders()
        input_files = self.pending_inputs_files()
        for file_name in input_files:
            self.process_input(file_name)

        if len(input_files) == 0:
            print("No data file found. As you were, soldier.")

    def process_input(self, file_path) -> None:
        print(f"Found input {file_path}! Let's get to work.")

        ring_data = load_json(file_path)

        # ring_data.data += self.my_secret()
        ring_data.data = ring_function(ring_data, self.secret_file)
        if ring_data.current_index < ring_length(ring_data) - 1:
            print("Going here with index = ", ring_data.current_index)
            ring_data.current_index += 1
            next_person = ring_data.ring[ring_data.current_index]
            self.send_data(next_person, ring_data)
        else:
            self.terminate_ring(ring_data)

        self.cleanup(file_path)

    def cleanup(self, file_path: Path) -> None:
        file_path.unlink()
        print(f"Done processing {file_path}, removed from pending inputs")

    def setup_folders(self) -> None:
        print("Setting up the necessary folders.")
        for folder in [self.running_folder, self.done_folder]:
            folder.mkdir(parents=True, exist_ok=True)

        # after this there will be files (so we can sync)
        permission = SyftPermission.mine_with_public_write(self.my_email)
        permission.ensure(self.ring_pipeline_path)

    def my_secret(self):
        with open(self.secret_file, "r") as secret_file:
            return int(secret_file.read().strip())

    def pending_inputs_files(self) -> List[Path]:
        return [
            self.running_folder / file for file in self.running_folder.glob("*.json")
        ]

    def write_json(self, file_path: Path, result: SimpleNamespace) -> None:
        print(f"Writing to {file_path}.")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(json.dumps(vars(result)))

    def send_data(self, email: str, data: SimpleNamespace) -> None:
        destination_datasite_path = Path(self.client.sync_folder) / email
        dest = (
            destination_datasite_path
            / "app_pipelines"
            / "ring"
            / "running"
            / "data.json"
        )
        self.write_json(dest, data)

    def terminate_ring(self, data: SimpleNamespace) -> None:
        print(f"Terminating ring, writing back to {self.done_folder}")
        self.write_json(self.done_folder / "data.json", data)


if __name__ == "__main__":
    runner = RingRunner()
    runner.run()
