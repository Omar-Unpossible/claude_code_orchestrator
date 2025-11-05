# Tetris Game Development - Milestone Plan

**Project**: Tetris Clone in Godot 4.5
**Location**: `/projects/test_tetrisgame/`
**Development Mode**: Headless (CLI-only, no GUI tools)
**Created**: 2025-11-04
**Godot Version**: 4.5.1.stable.official

---

## Project Overview

This document outlines the iterative development plan for creating a Tetris clone game using Godot 4.5 in headless mode. The project is broken down into 7 logical milestones, each with clear deliverables and success criteria.

### Key Constraints
- **Headless Development**: All files must be created via CLI/text editors (no Godot editor GUI)
- **Minimal Graphics**: Use simple ColorRect nodes (no sprite assets required)
- **Test Coverage**: Unit tests required for core game logic
- **Documentation**: Complete README and design documentation

### Technology Stack
- **Engine**: Godot 4.5.1
- **Language**: GDScript
- **Testing**: GUT (Godot Unit Testing) framework
- **Version Control**: Git

---

## Milestone Structure

Each milestone follows this pattern:
1. **Planning**: Define requirements and approach
2. **Implementation**: Create files and code
3. **Testing**: Verify functionality
4. **Documentation**: Update docs
5. **Validation**: Confirm success criteria met

---

## Milestone 1: Project Foundation & Setup

**Duration Estimate**: 30-45 minutes
**Dependencies**: None

### Deliverables

#### 1.1 Project Structure
- `/projects/test_tetrisgame/project.godot` - Godot project configuration
- `/projects/test_tetrisgame/.gitignore` - Git ignore rules
- `/projects/test_tetrisgame/README.md` - Project documentation
- `/projects/test_tetrisgame/DESIGN.md` - Technical design document
- Directory structure:
  ```
  test_tetrisgame/
  ├── project.godot
  ├── .gitignore
  ├── README.md
  ├── DESIGN.md
  ├── scenes/          (game scenes)
  ├── scripts/         (GDScript files)
  ├── tests/           (unit tests)
  └── docs/            (additional documentation)
  ```

#### 1.2 GUT Testing Framework
- Install GUT addon to `addons/gut/`
- Configure test runner
- Create sample test to verify setup

#### 1.3 Git Repository
- Initialize git repository
- Create initial commit
- Set up branch structure (main, develop)

### Success Criteria
- ✅ Godot project loads without errors (test with `godot --headless --quit`)
- ✅ GUT framework installed and test runner executes
- ✅ Sample test passes
- ✅ Git repository initialized with clean structure
- ✅ README contains project overview and setup instructions

### Validation Commands
```bash
# Test project loads
cd /projects/test_tetrisgame
godot --headless --quit --path .

# Test GUT framework
godot --headless --path . -s addons/gut/gut_cmdln.gd

# Verify git
git log --oneline
```

---

## Milestone 2: Core Game Data Structures

**Duration Estimate**: 1-1.5 hours
**Dependencies**: Milestone 1

### Deliverables

#### 2.1 Tetromino System (`scripts/tetromino.gd`)
- Tetromino class definition
- 7 piece types (I, O, T, S, Z, J, L)
- Shape definitions (4x4 matrix representations)
- Color assignments per piece type
- Rotation state management (4 rotation states)

#### 2.2 Game Board (`scripts/game_board.gd`)
- 10x20 grid representation
- Cell state tracking (empty, occupied, color)
- Boundary checking methods
- Row state queries

#### 2.3 Game Constants (`scripts/game_constants.gd`)
- Grid dimensions (10 columns, 20 rows)
- Cell size (for rendering)
- Colors for each tetromino type
- Game speed constants
- Scoring values

#### 2.4 Unit Tests (`tests/test_tetromino.gd`, `tests/test_game_board.gd`)
- Test tetromino creation
- Test shape definitions
- Test game board initialization
- Test boundary checking
- Test cell state management

### Success Criteria
- ✅ All 7 tetromino types defined with correct shapes
- ✅ Tetromino rotation logic implemented (90° clockwise)
- ✅ Game board correctly initializes 10x20 grid
- ✅ Boundary checking returns correct results
- ✅ All unit tests pass (≥95% code coverage for these modules)

### Validation Commands
```bash
# Run tetromino tests
godot --headless --path . -s addons/gut/gut_cmdln.gd -gtest=test_tetromino.gd

# Run game board tests
godot --headless --path . -s addons/gut/gut_cmdln.gd -gtest=test_game_board.gd
```

---

## Milestone 3: Core Game Logic

**Duration Estimate**: 2-2.5 hours
**Dependencies**: Milestone 2

### Deliverables

#### 3.1 Collision Detection (`scripts/collision_detector.gd`)
- Check tetromino-board collision
- Check tetromino-boundary collision
- Check tetromino-tetromino collision
- Rotation collision validation

#### 3.2 Piece Movement (`scripts/piece_controller.gd`)
- Move left/right with collision checking
- Move down with collision checking
- Rotation with wall kicks
- Hard drop functionality
- Lock piece to board

#### 3.3 Line Clearing (`scripts/line_manager.gd`)
- Detect full rows
- Clear full rows
- Shift rows down
- Calculate score multipliers (single, double, triple, Tetris)

#### 3.4 Score Manager (`scripts/score_manager.gd`)
- Track current score
- Track level
- Calculate points for line clears
- Level progression logic
- Speed adjustment per level

#### 3.5 Unit Tests
- `tests/test_collision_detector.gd` - All collision scenarios
- `tests/test_piece_controller.gd` - Movement and rotation
- `tests/test_line_manager.gd` - Line clearing logic
- `tests/test_score_manager.gd` - Scoring calculations

### Success Criteria
- ✅ Collision detection works for all piece types and orientations
- ✅ Pieces move correctly with collision boundaries
- ✅ Rotation includes wall kick behavior
- ✅ Line clearing correctly identifies and removes full rows
- ✅ Scoring matches standard Tetris rules
- ✅ All unit tests pass (≥95% code coverage)

### Validation Commands
```bash
# Run all core logic tests
godot --headless --path . -s addons/gut/gut_cmdln.gd -gdir=tests/
```

---

## Milestone 4: Game State Management

**Duration Estimate**: 1-1.5 hours
**Dependencies**: Milestone 3

### Deliverables

#### 4.1 Game State Machine (`scripts/game_state.gd`)
- State enumeration (TITLE, PLAYING, PAUSED, GAME_OVER)
- State transition logic
- State change signals
- Current state tracking

#### 4.2 Game Manager (`scripts/game_manager.gd`)
- Initialize new game
- Spawn next tetromino
- Handle piece locking
- Detect game over (top-out)
- Reset game state
- Pause/resume functionality

#### 4.3 Next Piece System (`scripts/next_piece_queue.gd`)
- Piece queue (preview next 1-3 pieces)
- Random piece generation (7-bag randomizer)
- Piece spawning logic

#### 4.4 Unit Tests
- `tests/test_game_state.gd` - State transitions
- `tests/test_game_manager.gd` - Game flow logic
- `tests/test_next_piece_queue.gd` - Randomizer behavior

### Success Criteria
- ✅ State machine correctly transitions between all states
- ✅ Game initializes with proper starting conditions
- ✅ Piece spawning uses 7-bag randomizer
- ✅ Game over correctly detected when pieces reach top
- ✅ Reset restores initial game state
- ✅ All unit tests pass (≥95% code coverage)

### Validation Commands
```bash
# Run game state tests
godot --headless --path . -s addons/gut/gut_cmdln.gd -gdir=tests/
```

---

## Milestone 5: Scene Structure & Input Handling

**Duration Estimate**: 1.5-2 hours
**Dependencies**: Milestone 4

### Deliverables

#### 5.1 Main Scene (`scenes/main.tscn`)
- Root node (Node2D)
- Scene switcher logic
- Global input handling setup

#### 5.2 Title Screen Scene (`scenes/title_screen.tscn`)
- Title label (Label node)
- "Play Now" button (ColorRect + Label)
- Simple background (ColorRect)
- Script: `scripts/title_screen.gd`

#### 5.3 Game Scene (`scenes/game.tscn`)
- Game board container (Node2D)
- Board cells (10x20 grid of ColorRect nodes)
- Current piece display (ColorRect nodes)
- Score display (Label)
- Level display (Label)
- Next piece preview (ColorRect nodes)
- Script: `scripts/game_scene.gd`

#### 5.4 Game Over Scene (`scenes/game_over.tscn`)
- "Game Over" label
- Final score display
- "Play Again?" button
- "Quit" button
- Script: `scripts/game_over_scene.gd`

#### 5.5 Input Handler (`scripts/input_handler.gd`)
- Map keyboard inputs to game actions
- Input buffering for fast presses
- Action definitions:
  - Arrow Left: Move left
  - Arrow Right: Move right
  - Arrow Down: Soft drop
  - Arrow Up (or Z): Rotate
  - Space: Hard drop
  - P: Pause
  - Escape: Quit to title

#### 5.6 Scene Configuration Files
- Create all `.tscn` files in text format (headless compatible)
- Define node hierarchies
- Set up node properties

### Success Criteria
- ✅ All scene files load without errors
- ✅ Title screen displays correctly
- ✅ Game scene contains all UI elements
- ✅ Game over scene displays correctly
- ✅ Input mapping configured in project settings
- ✅ Scene switching works (title → game → game over → title)
- ✅ Manual testing confirms scene structure

### Validation Commands
```bash
# Test each scene loads
godot --headless --path . --quit scenes/main.tscn
godot --headless --path . --quit scenes/title_screen.tscn
godot --headless --path . --quit scenes/game.tscn
godot --headless --path . --quit scenes/game_over.tscn
```

---

## Milestone 6: Game Integration & Rendering

**Duration Estimate**: 2-3 hours
**Dependencies**: Milestone 5

### Deliverables

#### 6.1 Board Renderer (`scripts/board_renderer.gd`)
- Update board cell colors based on game state
- Render locked pieces
- Render current active piece
- Render ghost piece (optional, shows landing position)

#### 6.2 UI Controller (`scripts/ui_controller.gd`)
- Update score display
- Update level display
- Update next piece preview
- Show/hide pause overlay

#### 6.3 Game Loop Integration (`scripts/game_scene.gd` - enhanced)
- Connect GameManager to rendering
- Implement gravity (automatic piece descent)
- Handle input from InputHandler
- Update UI every frame
- Handle pause state

#### 6.4 Scene Transitions (`scripts/main.gd`)
- Load title screen on start
- Transition to game on "Play Now"
- Transition to game over on game end
- Transition to title on quit
- Preserve game state during transitions (if needed)

#### 6.5 Integration Tests (`tests/test_integration.gd`)
- Test full game flow (title → game → game over)
- Test piece spawning and movement in game context
- Test line clearing updates score
- Test game over triggers correctly

### Success Criteria
- ✅ Game board renders correctly with colored cells
- ✅ Active piece updates in real-time
- ✅ Locked pieces persist on board
- ✅ Score and level update correctly
- ✅ Next piece preview shows correct piece
- ✅ Gravity works (pieces fall automatically)
- ✅ Scene transitions work smoothly
- ✅ Integration tests pass

### Validation Commands
```bash
# Run integration tests
godot --headless --path . -s addons/gut/gut_cmdln.gd -gtest=test_integration.gd

# Manual playtest (requires display)
godot --path . scenes/main.tscn
```

---

## Milestone 7: Polish, Testing & Documentation

**Duration Estimate**: 1.5-2 hours
**Dependencies**: Milestone 6

### Deliverables

#### 7.1 Bug Fixes & Polish
- Fix any remaining gameplay issues
- Tune game speed and difficulty curve
- Ensure all edge cases handled
- Code cleanup and refactoring

#### 7.2 Comprehensive Testing
- Run all unit tests
- Run integration tests
- Manual playtesting session
- Edge case testing (fast drops, rapid rotation, etc.)
- Fix any discovered bugs

#### 7.3 Code Quality
- Add missing docstrings
- Remove debug print statements
- Code formatting consistency
- Type hints where applicable

#### 7.4 Documentation Updates
- Update `README.md` with:
  - Complete setup instructions
  - How to run the game
  - How to run tests
  - Controls reference
  - Known issues (if any)
- Update `DESIGN.md` with:
  - Architecture overview
  - Class diagram
  - Key algorithms (rotation, collision, line clearing)
  - Future improvements
- Create `TESTING.md`:
  - Test coverage report
  - How to run tests
  - Test structure explanation

#### 7.5 Final Validation
- Complete test suite execution
- Generate coverage report
- Verify all success criteria from previous milestones

### Success Criteria
- ✅ All unit tests pass (100% passing rate)
- ✅ Test coverage ≥90% for core game logic modules
- ✅ No critical bugs remaining
- ✅ Game playable from start to finish
- ✅ All controls work as expected
- ✅ Documentation complete and accurate
- ✅ README provides clear instructions
- ✅ Git history clean with meaningful commits

### Validation Commands
```bash
# Run complete test suite
godot --headless --path . -s addons/gut/gut_cmdln.gd -gdir=tests/

# Check git history
git log --oneline --graph

# Verify project structure
tree -L 2

# Test game launches
godot --path . scenes/main.tscn
```

---

## Milestone Dependencies Graph

```
M1 (Foundation)
    ↓
M2 (Data Structures)
    ↓
M3 (Core Logic)
    ↓
M4 (State Management)
    ↓
M5 (Scenes & Input)
    ↓
M6 (Integration)
    ↓
M7 (Polish & Docs)
```

**Linear dependency**: Each milestone builds on the previous one. Milestones cannot be parallelized but provide natural breakpoints for iterative development.

---

## Execution Strategy

### Session Planning
Each milestone represents a logical work session that can be completed independently. Recommended approach:

1. **Session Start**: Review milestone goals and dependencies
2. **Implementation**: Follow deliverable checklist
3. **Testing**: Run validation commands continuously
4. **Documentation**: Update docs as you go
5. **Session End**: Commit work, verify success criteria
6. **Handoff**: Document any blockers or decisions for next session

### Headless Development Tips

#### Creating Scene Files
Since Godot scenes (`.tscn`) are text-based, create them manually:

```
[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://scripts/title_screen.gd" id="1"]

[node name="TitleScreen" type="Node2D"]
script = ExtResource("1")

[node name="Background" type="ColorRect" parent="."]
offset_right = 800.0
offset_bottom = 600.0
color = Color(0.1, 0.1, 0.15, 1)

[node name="TitleLabel" type="Label" parent="."]
offset_left = 300.0
offset_top = 200.0
offset_right = 500.0
offset_bottom = 250.0
text = "TETRIS"
```

#### Testing Without Display
- Use `godot --headless` flag for automated tests
- Use GUT framework for unit testing
- Use `--quit` flag to validate scene loading
- Manual playtesting requires display (save for final milestone)

#### Common Pitfalls
- ⚠️ Scene files must match exact format (indentation matters)
- ⚠️ Resource paths must use `res://` prefix
- ⚠️ Node names must be unique within parent
- ⚠️ ExtResource IDs must be sequential

---

## Test Coverage Targets

| Module | Target Coverage | Priority |
|--------|----------------|----------|
| Tetromino | ≥95% | Critical |
| GameBoard | ≥95% | Critical |
| CollisionDetector | ≥98% | Critical |
| LineManager | ≥95% | Critical |
| ScoreManager | ≥90% | High |
| GameState | ≥90% | High |
| GameManager | ≥85% | High |
| PieceController | ≥90% | High |
| NextPieceQueue | ≥85% | Medium |
| UI Controllers | ≥70% | Medium |
| Scene Scripts | ≥60% | Low |

**Overall Target**: ≥85% coverage for all core logic (scripts in `scripts/` directory)

---

## Success Metrics (Final)

Upon completion of all milestones, the project should meet:

### Functional Requirements
- ✅ Complete Tetris gameplay (spawn, move, rotate, lock, clear lines)
- ✅ Title screen with functional "Play Now" button
- ✅ Game over detection and display
- ✅ Score tracking and display
- ✅ "Play Again" functionality
- ✅ All keyboard controls working

### Technical Requirements
- ✅ Test coverage ≥85% overall
- ✅ All unit tests passing
- ✅ No critical bugs
- ✅ Game runs smoothly (60 FPS target)
- ✅ Headless test execution works

### Documentation Requirements
- ✅ README with setup and usage instructions
- ✅ DESIGN.md with architecture details
- ✅ TESTING.md with test documentation
- ✅ Code comments and docstrings
- ✅ Git history with meaningful commits

---

## Risk Assessment & Mitigation

### Risk 1: Headless Scene Creation Complexity
**Impact**: High
**Likelihood**: Medium
**Mitigation**:
- Start with minimal scene structures
- Test scene loading frequently with `--headless --quit`
- Reference Godot 4.5 scene format documentation
- Keep scenes simple (ColorRect only, no complex nodes)

### Risk 2: GUT Framework Setup Issues
**Impact**: Medium
**Likelihood**: Low
**Mitigation**:
- Install GUT in Milestone 1 and verify immediately
- Use stable GUT version compatible with Godot 4.5
- Create sample test to validate setup before proceeding

### Risk 3: Input Handling Without GUI Testing
**Impact**: Medium
**Likelihood**: Medium
**Mitigation**:
- Implement comprehensive unit tests for input logic
- Defer visual playtesting to final milestone
- Use print debugging and automated tests for validation

### Risk 4: Time Estimation Underruns
**Impact**: Low
**Likelihood**: Medium
**Mitigation**:
- Each milestone is independent - can pause between milestones
- Success criteria clearly defined for each milestone
- Can extend or split milestones if needed

---

## Next Steps

1. **Review this plan** with stakeholders/user
2. **Adjust milestones** if needed based on feedback
3. **Begin Milestone 1** - Project foundation setup
4. **Iterate** through remaining milestones sequentially

---

## Appendix A: File Checklist

**Milestone 1** (6 files):
- `/projects/test_tetrisgame/project.godot`
- `/projects/test_tetrisgame/.gitignore`
- `/projects/test_tetrisgame/README.md`
- `/projects/test_tetrisgame/DESIGN.md`
- `/projects/test_tetrisgame/addons/gut/` (directory + GUT files)
- Git repository (`.git/`)

**Milestone 2** (6 files):
- `scripts/tetromino.gd`
- `scripts/game_board.gd`
- `scripts/game_constants.gd`
- `tests/test_tetromino.gd`
- `tests/test_game_board.gd`
- `tests/test_game_constants.gd` (optional)

**Milestone 3** (9 files):
- `scripts/collision_detector.gd`
- `scripts/piece_controller.gd`
- `scripts/line_manager.gd`
- `scripts/score_manager.gd`
- `tests/test_collision_detector.gd`
- `tests/test_piece_controller.gd`
- `tests/test_line_manager.gd`
- `tests/test_score_manager.gd`
- `tests/test_helpers.gd` (optional test utilities)

**Milestone 4** (7 files):
- `scripts/game_state.gd`
- `scripts/game_manager.gd`
- `scripts/next_piece_queue.gd`
- `tests/test_game_state.gd`
- `tests/test_game_manager.gd`
- `tests/test_next_piece_queue.gd`
- `tests/test_integration_basic.gd` (optional)

**Milestone 5** (9 files):
- `scenes/main.tscn`
- `scenes/title_screen.tscn`
- `scenes/game.tscn`
- `scenes/game_over.tscn`
- `scripts/main.gd`
- `scripts/title_screen.gd`
- `scripts/game_scene.gd`
- `scripts/game_over_scene.gd`
- `scripts/input_handler.gd`

**Milestone 6** (5 files):
- `scripts/board_renderer.gd`
- `scripts/ui_controller.gd`
- Enhanced: `scripts/game_scene.gd`
- Enhanced: `scripts/main.gd`
- `tests/test_integration.gd`

**Milestone 7** (3 files):
- Enhanced: `README.md`
- Enhanced: `DESIGN.md`
- `TESTING.md`

**Total Estimated Files**: ~45 files (scripts, tests, scenes, docs)

---

## Appendix B: Godot Project Configuration

**Minimal `project.godot`** (Milestone 1):

```
; Engine configuration file.
; Generated by Godot 4.5.1

config_version=5

[application]

config/name="Tetris Clone"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.5", "GL Compatibility")

[display]

window/size/viewport_width=800
window/size/viewport_height=600
window/size/resizable=false

[input]

move_left={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":0,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":4194319,"physical_keycode":0,"key_label":0,"unicode":0,"echo":false,"script":null)
]
}
move_right={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":0,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":4194321,"physical_keycode":0,"key_label":0,"unicode":0,"echo":false,"script":null)
]
}
move_down={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":0,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":4194322,"physical_keycode":0,"key_label":0,"unicode":0,"echo":false,"script":null)
]
}
rotate={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":0,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":4194320,"physical_keycode":0,"key_label":0,"unicode":0,"echo":false,"script":null)
, Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":0,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":90,"physical_keycode":0,"key_label":0,"unicode":0,"echo":false,"script":null)
]
}
hard_drop={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":0,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":32,"physical_keycode":0,"key_label":0,"unicode":0,"echo":false,"script":null)
]
}
pause={
"deadzone": 0.5,
"events": [Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":0,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":80,"physical_keycode":0,"key_label":0,"unicode":0,"echo":false,"script":null)
]
}

[rendering]

renderer/rendering_method="gl_compatibility"
```

---

**End of Milestone Plan**
