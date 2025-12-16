## File Descriptions

### `main.py`
Entry point of the project

**Responsible for:**
* Initializing the game/engine
* Loading the selected strategy
* Running simulations or matches

### `engine_core.py`
Contains the core game logic and engine implementation

**Responsibilities include:**
* Defining game state
* Managing turns / rounds
* Enforcing rules
* Calling strategy hooks (e.g., decision functions)

Acts as the interface between the engine and strategies.

### `mystrat.py` (User-editable file)
The only file that is allowed to be edited for final submission

**Contains the custom strategy implementation**

**Must:**
* Follow the function signatures expected by `engine_core.py`
* Work correctly when imported by the original `main.py`
* Avoid changing any external interfaces

This is the file that will be evaluated.

### ⚠️ Important:
During evaluation, only `mystrat.py` will be replaced.
All other files (`main.py`, `engine_core.py`) will remain unchanged.

### `dummy_strategies.py`
Contains example / baseline strategies

**Useful for:**
* Understanding expected function signatures
* Testing engine behavior
* Debugging strategy interactions

Not used for final evaluation.

**NOTE:**
If you want to test multiple strategies you can either change the dummy strategies or make a new class in `mystrat.py` and import accordingly.

## Running the Project

You have to firstly install treys using:

```bash
pip install treys
```

Then run the engine by running following command:

```bash
python main.py