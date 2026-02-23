# Summary
Renamed `sakshi/` folder to `backend/` and created `frontend/` folder to prepare the project for full-stack scalability. Updated `.gitignore` and added project-level documentation.

## Key Decisions
- Renamed `sakshi/` → `backend/` for clearer separation of concerns
- Created `frontend/` folder as placeholder for future UI development
- Added comprehensive `README.md` at project root documenting new structure
- Removed `*.sh` and `test/` from `.gitignore` to track essential scripts and utilities

## Current State
- All backend code moved to `/backend/` with git history preserved (56 files renamed)
- Frontend folder created at `/frontend/` with placeholder README
- Docker, Makefile, API code all functional in new location (no path changes needed)
- Changes committed (916608d) and pushed to origin/main
- Backend API runs from `/backend/main.py` (relative paths still work)

## Known Limitations
- Frontend folder is empty (placeholder only)
- `docker-compose.yml` and `Dockerfile` still in backend folder (not at root)
- Virtual environment `yolo_clean/` remains at project root

## Rationale
- **Folder rename**: "sakshi" was non-descriptive; "backend" clearly indicates server-side code
- **Frontend folder**: Prepares for React/Vue/Angular addition without restructuring again
- **Git renames**: Used `mv` + `git add -A` to preserve file history
- **.gitignore update**: Scripts like `setup_db.sh` and `test_api.sh` are essential for deployment

## Next Steps
1. Update any external CI/CD pipelines or deployment scripts referencing old `sakshi/` path
2. Choose frontend framework (React recommended for this stack)
3. Consider moving `docker-compose.yml` to root for multi-service orchestration
4. Add frontend-specific `.dockerignore` when frontend is implemented
5. Update any documentation referencing old folder structure

## Things NOT To Do
- Do NOT create separate git repos for frontend/backend (monorepo works for this project size)
- Do NOT manually recreate files - all renames preserved git history
- Do NOT change import paths in Python code (relative imports still work)
- Do NOT ignore `test/` directory (contains ROI utilities needed for debugging)
