"""Simple web UI for Agent Management Suite."""

import json
import webbrowser
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from sync_agents import AgentSync
from utils.exclusion_manager import ExclusionManager

app = FastAPI(title="Agent Management Suite")

# Templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Global syncer instance (lazy loaded)
_syncer: Optional[AgentSync] = None
_exclusion_manager: Optional[ExclusionManager] = None


def get_syncer() -> AgentSync:
    """Get or create the syncer instance."""
    global _syncer
    if _syncer is None:
        _syncer = AgentSync()
        _syncer.load_all_claude()
    return _syncer


def get_exclusion_manager() -> ExclusionManager:
    """Get or create the exclusion manager instance."""
    global _exclusion_manager
    if _exclusion_manager is None:
        _exclusion_manager = ExclusionManager()
    return _exclusion_manager


def reload_syncer():
    """Force reload of syncer data."""
    global _syncer
    _syncer = None
    return get_syncer()


# ============ Routes ============

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Dashboard home page."""
    syncer = get_syncer()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "agent_count": len(syncer.agents),
        "skill_count": len(syncer.skills),
        "plugin_count": len(syncer.plugins),
        "command_count": len(syncer.commands),
        "hook_count": len(syncer.hooks),
    })


@app.get("/agents", response_class=HTMLResponse)
async def agents_page(request: Request, search: str = ""):
    """Agent browser page."""
    syncer = get_syncer()
    em = get_exclusion_manager()

    agents = syncer.agents
    if search:
        search_lower = search.lower()
        agents = [a for a in agents if search_lower in a.name.lower()
                  or search_lower in (a.description or "").lower()]

    # Add exclusion status to each agent
    agents_with_status = []
    for agent in sorted(agents, key=lambda a: a.name):
        status = em.get_exclusion_status("agent", agent.name)
        agents_with_status.append({
            "agent": agent,
            "excluded": status["is_excluded"],
            "explicit": status["is_explicit"],
        })

    return templates.TemplateResponse("agents.html", {
        "request": request,
        "agents": agents_with_status,
        "search": search,
        "total": len(syncer.agents),
    })


@app.get("/agents/{name}", response_class=HTMLResponse)
async def agent_detail(request: Request, name: str):
    """Agent detail page."""
    syncer = get_syncer()
    em = get_exclusion_manager()

    agent = next((a for a in syncer.agents if a.name == name), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    status = em.get_exclusion_status("agent", agent.name)

    return templates.TemplateResponse("agent_detail.html", {
        "request": request,
        "agent": agent,
        "excluded": status["is_excluded"],
        "explicit": status["is_explicit"],
    })


@app.post("/agents/{name}/toggle-exclusion")
async def toggle_agent_exclusion(name: str):
    """Toggle agent exclusion status."""
    em = get_exclusion_manager()
    is_excluded, msg = em.toggle_exclusion("agent", name)
    return RedirectResponse(url=f"/agents/{name}", status_code=303)


@app.get("/skills", response_class=HTMLResponse)
async def skills_page(request: Request, search: str = ""):
    """Skill browser page."""
    syncer = get_syncer()
    em = get_exclusion_manager()

    skills = syncer.skills
    if search:
        search_lower = search.lower()
        skills = [s for s in skills if search_lower in s.name.lower()
                  or search_lower in (s.description or "").lower()]

    skills_with_status = []
    for skill in sorted(skills, key=lambda s: s.name):
        status = em.get_exclusion_status("skill", skill.name)
        skills_with_status.append({
            "skill": skill,
            "excluded": status["is_excluded"],
        })

    return templates.TemplateResponse("skills.html", {
        "request": request,
        "skills": skills_with_status,
        "search": search,
        "total": len(syncer.skills),
    })


@app.get("/skills/{name}", response_class=HTMLResponse)
async def skill_detail(request: Request, name: str):
    """Skill detail page."""
    syncer = get_syncer()
    em = get_exclusion_manager()

    skill = next((s for s in syncer.skills if s.name == name), None)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    status = em.get_exclusion_status("skill", skill.name)

    # Get skill content
    skill_md = skill.source_path / "SKILL.md"
    content = skill_md.read_text() if skill_md.exists() else ""

    return templates.TemplateResponse("skill_detail.html", {
        "request": request,
        "skill": skill,
        "content": content,
        "excluded": status["is_excluded"],
    })


@app.post("/skills/{name}/toggle-exclusion")
async def toggle_skill_exclusion(name: str):
    """Toggle skill exclusion status."""
    em = get_exclusion_manager()
    em.toggle_exclusion("skill", name)
    return RedirectResponse(url=f"/skills/{name}", status_code=303)


@app.get("/plugins", response_class=HTMLResponse)
async def plugins_page(request: Request):
    """Plugin browser page."""
    syncer = get_syncer()
    em = get_exclusion_manager()

    plugins_with_status = []
    for plugin in sorted(syncer.plugins, key=lambda p: p.name):
        status = em.get_exclusion_status("plugin", plugin.name)

        # Count components
        cmd_count = len(list((plugin.source_path / "commands").glob("*.md"))) if (plugin.source_path / "commands").exists() else 0
        agent_count = len(list((plugin.source_path / "agents").glob("*.md"))) if (plugin.source_path / "agents").exists() else 0
        skill_count = len([d for d in (plugin.source_path / "skills").iterdir() if d.is_dir()]) if (plugin.source_path / "skills").exists() else 0

        plugins_with_status.append({
            "plugin": plugin,
            "excluded": status["is_excluded"],
            "cmd_count": cmd_count,
            "agent_count": agent_count,
            "skill_count": skill_count,
        })

    return templates.TemplateResponse("plugins.html", {
        "request": request,
        "plugins": plugins_with_status,
        "total": len(syncer.plugins),
    })


@app.get("/plugins/{name}", response_class=HTMLResponse)
async def plugin_detail(request: Request, name: str):
    """Plugin detail page."""
    syncer = get_syncer()
    em = get_exclusion_manager()

    plugin = next((p for p in syncer.plugins if p.name == name), None)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")

    status = em.get_exclusion_status("plugin", plugin.name)

    # Get components
    commands = []
    agents = []
    skills = []

    cmd_dir = plugin.source_path / "commands"
    if cmd_dir.exists():
        for cmd_file in cmd_dir.glob("*.md"):
            commands.append({"name": cmd_file.stem, "path": cmd_file})

    agent_dir = plugin.source_path / "agents"
    if agent_dir.exists():
        for agent_file in agent_dir.glob("*.md"):
            agents.append({"name": agent_file.stem, "path": agent_file})

    skills_dir = plugin.source_path / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                skills.append({"name": skill_dir.name, "path": skill_dir})

    return templates.TemplateResponse("plugin_detail.html", {
        "request": request,
        "plugin": plugin,
        "excluded": status["is_excluded"],
        "commands": commands,
        "agents": agents,
        "skills": skills,
    })


@app.post("/plugins/{name}/toggle-exclusion")
async def toggle_plugin_exclusion(name: str):
    """Toggle plugin exclusion status."""
    em = get_exclusion_manager()
    em.toggle_exclusion("plugin", name)
    return RedirectResponse(url=f"/plugins/{name}", status_code=303)


@app.get("/hooks", response_class=HTMLResponse)
async def hooks_page(request: Request):
    """Hook browser page."""
    syncer = get_syncer()

    # Group hooks by event
    hooks_by_event = {}
    for hook in syncer.hooks:
        hooks_by_event.setdefault(hook.event, []).append(hook)

    return templates.TemplateResponse("hooks.html", {
        "request": request,
        "hooks_by_event": hooks_by_event,
        "total": len(syncer.hooks),
    })


@app.get("/sync", response_class=HTMLResponse)
async def sync_page(request: Request):
    """Platform sync page."""
    syncer = get_syncer()

    # Get platform status
    from pathlib import Path
    home = Path.home()

    platforms = [
        {"name": "Codex CLI", "path": home / ".codex", "type": "compatible"},
        {"name": "Gemini CLI", "path": home / ".gemini", "type": "compatible"},
        {"name": "Antigravity", "path": home / ".agent", "type": "compatible"},
        {"name": "Continue", "path": home / ".continue", "type": "compatible"},
        {"name": "OpenCode", "path": home / ".opencode", "type": "compatible"},
        {"name": "Trae", "path": home / ".trae", "type": "compatible"},
        {"name": "Cursor", "path": home / ".cursor", "type": "conversion"},
        {"name": "Windsurf", "path": home / ".windsurf", "type": "conversion"},
        {"name": "Roo Code", "path": home / ".roo", "type": "conversion"},
        {"name": "Kiro", "path": home / ".kiro", "type": "conversion"},
    ]

    for p in platforms:
        p["installed"] = p["path"].exists()

    return templates.TemplateResponse("sync.html", {
        "request": request,
        "platforms": platforms,
        "agent_count": len(syncer.agents),
        "skill_count": len(syncer.skills),
    })


@app.post("/sync/run")
async def run_sync(platforms: str = Form(...)):
    """Run sync to selected platforms."""
    syncer = get_syncer()
    selected = platforms.split(",") if platforms else []

    # TODO: Implement actual sync
    # For now, just redirect back
    return RedirectResponse(url="/sync?synced=1", status_code=303)


@app.get("/reload")
async def reload_data():
    """Reload all data from Claude Code."""
    reload_syncer()
    return RedirectResponse(url="/", status_code=303)


def run_server(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True):
    """Run the web server."""
    import uvicorn

    if open_browser:
        webbrowser.open(f"http://{host}:{port}")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
