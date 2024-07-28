import asyncio
import threading
from tkinter import *
from tkinter import ttk
from ocpp.v16 import ChargePoint as cp
from ocpp.v16 import call_result
from ocpp.v16.enums import RegistrationStatus
from ocpp.routing import on
import websockets
import time

VOLTAGE = 230

class EVCharger:
    def __init__(self, id):
        self.id = id
        self.current = 0
        self.status = "Available"
        self.setpoint_current = 8

    def update_status(self):
        if self.current > 0:
            self.status = "Charging"
        else:
            self.status = "Available"

    def simulate_charging(self):
        try:
            while True:
                if self.current == 0:
                    time.sleep(5)
                    self.current = 8
                self.update_status()
                time.sleep(1)
        except Exception as e:
            print(f"Error in charger {self.id} simulation: {e}")

    def get_active_power(self):
        return self.current * VOLTAGE
    
    def get_status_code(self):
        return 3 if self.status == "Charging" else 4

class ChargePoint(cp):
    @on('BootNotification')
    async def on_boot_notification(self, **kwargs):
        print(f"BootNotification from {self.id}: {kwargs}")
        return call_result.BootNotification(
            current_time='2023-01-01T00:00:00Z',
            interval=10,
            status=RegistrationStatus.accepted
        )

    @on('StatusNotification')
    async def on_status_notification(self, **kwargs):
        print(f"StatusNotification from {self.id}: {kwargs}")
        return call_result.StatusNotification()

async def on_connect(websocket, path):
    charge_point_id = path.strip('/')
    charge_point = ChargePoint(charge_point_id, websocket)
    await charge_point.start()

class ChargerGUI:
    def __init__(self, root, chargers):
        self.root = root
        self.chargers = chargers
        self.root.title("EV Charger Simulation")
        self.tree_items = {}
        self.create_widgets()
        self.update_gui()

    def create_widgets(self):
        self.tree = ttk.Treeview(self.root, columns=('ID', 'Current', 'Setpoint Current', 'Active Power', 'Status Code', 'Status'), show='headings')
        self.tree.heading('ID', text='ID')
        self.tree.heading('Current', text='Current')
        self.tree.heading('Setpoint Current', text='Setpoint Current')
        self.tree.heading('Active Power', text='Active Power (W)')
        self.tree.heading('Status Code', text='Status Code')
        self.tree.heading('Status', text='Status')
        self.tree.pack(fill=BOTH, expand=True)

        self.update_frame = Frame(self.root)
        self.update_frame.pack()

        self.charger_id_label = Label(self.update_frame, text="Charger ID:")
        self.charger_id_label.grid(row=0, column=0)

        self.charger_id_entry = Entry(self.update_frame)
        self.charger_id_entry.grid(row=0, column=1)

        self.setpoint_label = Label(self.update_frame, text="Setpoint Current:")
        self.setpoint_label.grid(row=1, column=0)

        self.setpoint_entry = Entry(self.update_frame)
        self.setpoint_entry.grid(row=1, column=1)

        self.current_label = Label(self.update_frame, text="Current:")
        self.current_label.grid(row=2, column=0)

        self.current_entry = Entry(self.update_frame)
        self.current_entry.grid(row=2, column=1)

        self.update_button = Button(self.update_frame, text="Update", command=self.manual_update_charger)
        self.update_button.grid(row=3, columnspan=2)

    def update_tree(self):
        for charger in self.chargers:
            if charger.id in self.tree_items:
                self.tree.item(self.tree_items[charger.id], values=(charger.id, charger.current, charger.setpoint_current, charger.get_active_power(), charger.get_status_code(), charger.status))
            else:
                item_id = self.tree.insert('', 'end', values=(charger.id, charger.current, charger.setpoint_current, charger.get_active_power(), charger.get_status_code(), charger.status))
                self.tree_items[charger.id] = item_id

    def manual_update_charger(self):
        try:
            charger_id = int(self.charger_id_entry.get())
            setpoint_current = int(self.setpoint_entry.get())
            current = int(self.current_entry.get())

            charger = next((c for c in self.chargers if c.id == charger_id), None)
            if charger:
                charger.setpoint_current = setpoint_current
                charger.current = current
                charger.update_status()

            self.update_tree()
        except ValueError:
            print("Please enter valid integer values for Charger ID, Setpoint Current, and Current.")

    def update_gui(self):
        self.update_tree()
        self.root.after(1000, self.update_gui)

def start_ocpp_server():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    server = websockets.serve(on_connect, 'localhost', 9000)
    try:
        loop.run_until_complete(server)
        loop.run_forever()
    except Exception as e:
        print(f"Error in OCPP server: {e}")
    finally:
        loop.close()

def start_gui(chargers):
    root = Tk()
    gui = ChargerGUI(root, chargers)
    root.mainloop()

if __name__ == "__main__":
    num_chargers = int(input("Enter the number of chargers to simulate: "))
    chargers = [EVCharger(id=i) for i in range(num_chargers)]

    for charger in chargers:
        threading.Thread(target=charger.simulate_charging, daemon=True).start()

    threading.Thread(target=start_ocpp_server, daemon=True).start()
    start_gui(chargers)
