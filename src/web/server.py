"""Web UI for Agent Management Suite with full functionality."""

import asyncio
import json
import tempfile
import uuid
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from sync_agents import AgentSync
from utils.exclusion_manager import ExclusionManager
from utils.workflow_manager import WorkflowManager
from utils.connection_monitor import ConnectionMonitor

app = FastAPI(title="Agent Management Suite")

# Sync progress tracking
_sync_progress: dict = {"status": "idle", "message": "", "platform": "", "step": 0, "total": 0}

# Templates
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Global syncer instance (lazy loaded)
_syncer: Optional[AgentSync] = None
_exclusion_manager: Optional[ExclusionManager] = None
_workflow_manager: Optional[WorkflowManager] = None
_connection_monitor: Optional[ConnectionMonitor] = None

# Workflow execution state
_workflow_runs: dict = {}  # run_id -> run state


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


def get_workflow_manager() -> WorkflowManager:
    """Get or create the workflow manager instance."""
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = WorkflowManager()
    return _workflow_manager


def get_connection_monitor() -> ConnectionMonitor:
    """Get or create the connection monitor instance."""
    global _connection_monitor
    if _connection_monitor is None:
        _connection_monitor = ConnectionMonitor()
    return _connection_monitor


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
async def run_sync(
    request: Request,
    platforms: str = Form(...),
    respect_exclusions: bool = Form(False)
):
    """Run sync to selected platforms."""
    global _sync_progress
    syncer = get_syncer()
    em = get_exclusion_manager()
    selected = [p.strip() for p in platforms.split(",") if p.strip()]

    if not selected:
        return RedirectResponse(url="/sync?error=no_platforms", status_code=303)

    # Platform name mapping
    platform_map = {
        "Codex CLI": "codex",
        "Gemini CLI": "gemini",
        "Antigravity": "antigravity",
        "Continue": "continue",
        "OpenCode": "opencode",
        "Trae": "trae",
        "Cursor": "cursor",
        "Windsurf": "windsurf",
        "Roo Code": "roocode",
        "Kiro": "kiro",
        "GitHub Copilot": "copilot",
        "Aider": "aider",
    }

    synced_count = 0
    errors = []

    for platform_name in selected:
        platform_id = platform_map.get(platform_name, platform_name.lower().replace(" ", ""))

        try:
            _sync_progress = {
                "status": "syncing",
                "message": f"Syncing to {platform_name}...",
                "platform": platform_name,
                "step": synced_count + 1,
                "total": len(selected)
            }

            # Apply exclusions if requested
            if respect_exclusions:
                # Filter components before sync
                syncer.agents, _ = em.filter_components(syncer.agents, "agent", "sync")
                syncer.skills, _ = em.filter_components(syncer.skills, "skill", "sync")
                syncer.commands, _ = em.filter_components(syncer.commands, "command", "sync")
                syncer.plugins, _ = em.filter_components(syncer.plugins, "plugin", "sync")

            # Call the appropriate sync method
            syncer.sync_platform(platform_id)
            synced_count += 1

        except Exception as e:
            errors.append(f"{platform_name}: {str(e)}")

    _sync_progress = {"status": "idle", "message": "", "platform": "", "step": 0, "total": 0}

    # Reload to get fresh state
    reload_syncer()

    if errors:
        error_str = "; ".join(errors)
        return RedirectResponse(url=f"/sync?synced={synced_count}&errors={len(errors)}", status_code=303)

    return RedirectResponse(url=f"/sync?synced={synced_count}", status_code=303)


@app.get("/reload")
async def reload_data():
    """Reload all data from Claude Code."""
    reload_syncer()
    return RedirectResponse(url="/", status_code=303)


# ============ Export/Import ============

@app.get("/export", response_class=HTMLResponse)
async def export_page(request: Request):
    """Export configuration page."""
    syncer = get_syncer()
    em = get_exclusion_manager()

    # Get counts with exclusion info
    agents_included, agents_excluded = em.filter_components(syncer.agents, "agent", "export")
    skills_included, skills_excluded = em.filter_components(syncer.skills, "skill", "export")
    plugins_included, plugins_excluded = em.filter_components(syncer.plugins, "plugin", "export")
    commands_included, commands_excluded = em.filter_components(syncer.commands, "command", "export")

    return templates.TemplateResponse("export.html", {
        "request": request,
        "agents_total": len(syncer.agents),
        "agents_excluded": len(agents_excluded),
        "skills_total": len(syncer.skills),
        "skills_excluded": len(skills_excluded),
        "plugins_total": len(syncer.plugins),
        "plugins_excluded": len(plugins_excluded),
        "commands_total": len(syncer.commands),
        "commands_excluded": len(commands_excluded),
    })


@app.post("/export/download")
async def download_export(
    include_plugins: bool = Form(True),
    respect_exclusions: bool = Form(False)
):
    """Create and download export bundle."""
    syncer = get_syncer()
    em = get_exclusion_manager()

    # Create temp file for bundle
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        output_path = Path(tmp.name)

    # If respecting exclusions, filter before export
    if respect_exclusions:
        syncer.agents, _ = em.filter_components(syncer.agents, "agent", "export")
        syncer.skills, _ = em.filter_components(syncer.skills, "skill", "export")
        syncer.commands, _ = em.filter_components(syncer.commands, "command", "export")
        syncer.plugins, _ = em.filter_components(syncer.plugins, "plugin", "export")

    bundle_path = syncer.export_bundle(output_path, include_plugins=include_plugins)

    return FileResponse(
        path=str(bundle_path),
        filename=f"claude-bundle-{bundle_path.stem.split('-')[-1]}.tar.gz",
        media_type="application/gzip"
    )


@app.get("/import", response_class=HTMLResponse)
async def import_page(request: Request, success: str = None, error: str = None):
    """Import configuration page."""
    return templates.TemplateResponse("import.html", {
        "request": request,
        "success": success,
        "error": error,
    })


@app.post("/import/upload")
async def upload_import(
    bundle: UploadFile = File(...),
    merge: bool = Form(False),
    backup: bool = Form(True)
):
    """Upload and import bundle."""
    syncer = get_syncer()

    # Save uploaded file
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        content = await bundle.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        success = syncer.import_bundle(tmp_path, merge=merge, backup=backup)
        if success:
            reload_syncer()
            return RedirectResponse(url="/import?success=1", status_code=303)
        else:
            return RedirectResponse(url="/import?error=import_failed", status_code=303)
    except Exception as e:
        return RedirectResponse(url=f"/import?error={str(e)[:50]}", status_code=303)
    finally:
        tmp_path.unlink(missing_ok=True)


# ============ Commands ============

@app.get("/commands", response_class=HTMLResponse)
async def commands_page(request: Request, search: str = ""):
    """Command browser page."""
    syncer = get_syncer()
    em = get_exclusion_manager()

    commands = syncer.commands
    if search:
        search_lower = search.lower()
        commands = [c for c in commands if search_lower in c.name.lower()
                   or search_lower in (c.description or "").lower()]

    commands_with_status = []
    for cmd in sorted(commands, key=lambda c: c.name):
        status = em.get_exclusion_status("command", cmd.name)
        commands_with_status.append({
            "command": cmd,
            "excluded": status["is_excluded"],
            "explicit": status["is_explicit"],
        })

    return templates.TemplateResponse("commands.html", {
        "request": request,
        "commands": commands_with_status,
        "search": search,
        "total": len(syncer.commands),
    })


@app.get("/commands/{name}", response_class=HTMLResponse)
async def command_detail(request: Request, name: str):
    """Command detail page."""
    syncer = get_syncer()
    em = get_exclusion_manager()

    command = next((c for c in syncer.commands if c.name == name), None)
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")

    status = em.get_exclusion_status("command", command.name)

    return templates.TemplateResponse("command_detail.html", {
        "request": request,
        "command": command,
        "excluded": status["is_excluded"],
        "explicit": status["is_explicit"],
    })


@app.post("/commands/{name}/toggle-exclusion")
async def toggle_command_exclusion(name: str):
    """Toggle command exclusion status."""
    em = get_exclusion_manager()
    em.toggle_exclusion("command", name)
    return RedirectResponse(url=f"/commands/{name}", status_code=303)


# ============ Exclusion Rules ============

@app.get("/exclusions", response_class=HTMLResponse)
async def exclusions_page(request: Request):
    """Exclusion rules management page."""
    em = get_exclusion_manager()
    syncer = get_syncer()

    rules = em.list_rules()
    summary = em.get_summary()

    # Count how many components are currently excluded
    excluded_counts = {
        "agents": len([a for a in syncer.agents if em.is_excluded("agent", a.name)]),
        "skills": len([s for s in syncer.skills if em.is_excluded("skill", s.name)]),
        "plugins": len([p for p in syncer.plugins if em.is_excluded("plugin", p.name)]),
        "commands": len([c for c in syncer.commands if em.is_excluded("command", c.name)]),
    }

    return templates.TemplateResponse("exclusions.html", {
        "request": request,
        "rules": rules,
        "summary": summary,
        "excluded_counts": excluded_counts,
        "total_agents": len(syncer.agents),
        "total_skills": len(syncer.skills),
        "total_plugins": len(syncer.plugins),
        "total_commands": len(syncer.commands),
    })


@app.post("/exclusions/add")
async def add_exclusion_rule(
    component_type: str = Form(...),
    pattern: str = Form(...),
    reason: str = Form(""),
    exclude_sync: bool = Form(True),
    exclude_export: bool = Form(True)
):
    """Add a new exclusion rule."""
    em = get_exclusion_manager()
    em.add_rule(component_type, pattern, reason, exclude_sync, exclude_export)
    return RedirectResponse(url="/exclusions", status_code=303)


@app.post("/exclusions/{rule_id}/delete")
async def delete_exclusion_rule(rule_id: str):
    """Delete an exclusion rule."""
    em = get_exclusion_manager()
    em.remove_rule(rule_id)
    return RedirectResponse(url="/exclusions", status_code=303)


# ============ Workflows ============

@app.get("/workflows", response_class=HTMLResponse)
async def workflows_page(request: Request, search: str = ""):
    """Workflow list page."""
    wm = get_workflow_manager()

    workflows = wm.list_workflows()
    if search:
        search_lower = search.lower()
        workflows = [w for w in workflows if search_lower in w.name.lower()
                     or search_lower in (w.description or "").lower()]

    return templates.TemplateResponse("workflows.html", {
        "request": request,
        "workflows": sorted(workflows, key=lambda w: w.name),
        "search": search,
        "total": len(wm.list_workflows()),
    })


@app.get("/workflows/new", response_class=HTMLResponse)
async def workflow_designer_new(request: Request):
    """New workflow designer page."""
    syncer = get_syncer()
    agents = [{"name": a.name, "description": a.description} for a in syncer.agents]

    return templates.TemplateResponse("workflow_designer.html", {
        "request": request,
        "workflow": None,
        "workflow_json": "null",
        "agents": agents,
        "is_new": True,
    })


@app.get("/workflows/{workflow_id}", response_class=HTMLResponse)
async def workflow_designer_edit(request: Request, workflow_id: str):
    """Edit workflow designer page."""
    wm = get_workflow_manager()
    syncer = get_syncer()

    workflow = wm.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    visual_data = wm.to_visual_format(workflow_id)
    agents = [{"name": a.name, "description": a.description} for a in syncer.agents]

    return templates.TemplateResponse("workflow_designer.html", {
        "request": request,
        "workflow": workflow,
        "workflow_json": json.dumps(visual_data),
        "agents": agents,
        "is_new": False,
    })


@app.post("/api/workflows")
async def create_workflow(request: Request):
    """Create a new workflow from visual format."""
    wm = get_workflow_manager()
    data = await request.json()

    workflow = wm.from_visual_format(data)
    return {"success": True, "id": workflow.id}


@app.put("/api/workflows/{workflow_id}")
async def update_workflow(request: Request, workflow_id: str):
    """Update an existing workflow from visual format."""
    wm = get_workflow_manager()
    data = await request.json()

    if workflow_id not in wm.workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")

    data["id"] = workflow_id
    workflow = wm.from_visual_format(data)
    return {"success": True, "id": workflow.id}


@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow."""
    wm = get_workflow_manager()

    if not wm.delete_workflow(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")

    return {"success": True}


@app.get("/api/workflows/{workflow_id}")
async def get_workflow_json(workflow_id: str):
    """Get workflow as JSON."""
    wm = get_workflow_manager()

    visual_data = wm.to_visual_format(workflow_id)
    if not visual_data:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return visual_data


@app.get("/api/agents/list")
async def list_agents_api():
    """Get available agents for dropdown."""
    syncer = get_syncer()
    return [
        {"name": a.name, "description": a.description or ""}
        for a in sorted(syncer.agents, key=lambda a: a.name)
    ]


# ============ Workflow Export ============

@app.post("/api/workflows/{workflow_id}/export")
async def export_workflow(request: Request, workflow_id: str):
    """Export workflow to Claude Code format (skill, command, or prompt)."""
    wm = get_workflow_manager()

    workflow = wm.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    data = await request.json()
    export_type = data.get("export_type", "skill")

    try:
        if export_type == "skill":
            path = wm.export_as_skill(workflow_id)
        elif export_type == "command":
            path = wm.export_as_command(workflow_id)
        elif export_type == "prompt":
            path = wm.export_as_prompt(workflow_id)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid export type: {export_type}")

        if not path:
            raise HTTPException(status_code=500, detail="Failed to generate export")

        return {"success": True, "path": str(path), "type": export_type}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/{workflow_id}/exports")
async def get_workflow_exports(workflow_id: str):
    """Check what exports exist for this workflow."""
    wm = get_workflow_manager()

    workflow = wm.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    status = wm.get_export_status(workflow_id)
    paths = wm.get_export_paths(workflow_id)

    return {
        "skill": status["skill"],
        "command": status["command"],
        "prompt": status["prompt"],
        "paths": {
            "skill": str(paths["skill"]) if status["skill"] else None,
            "command": str(paths["command"]) if status["command"] else None,
            "prompt": str(paths["prompt"]) if status["prompt"] else None,
        }
    }


@app.delete("/api/workflows/{workflow_id}/exports")
async def delete_workflow_exports(workflow_id: str):
    """Delete all exports for a workflow."""
    wm = get_workflow_manager()

    workflow = wm.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    results = wm.delete_exports(workflow_id)
    return {"success": True, "deleted": results}


@app.get("/api/workflows/{workflow_id}/analyze")
async def analyze_workflow(workflow_id: str):
    """Analyze workflow complexity and get export recommendation."""
    wm = get_workflow_manager()

    workflow = wm.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    analysis = wm.analyze_workflow_complexity(workflow_id)
    return analysis


@app.post("/api/workflows/{workflow_id}/smart-export")
async def smart_export_workflow(workflow_id: str):
    """Intelligently export workflow based on complexity analysis."""
    wm = get_workflow_manager()

    workflow = wm.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    results = wm.smart_export(workflow_id)
    return {"success": True, **results}


# ============ Workflow Execution ============

@app.get("/workflows/{workflow_id}/run", response_class=HTMLResponse)
async def workflow_run_page(request: Request, workflow_id: str):
    """Workflow execution page."""
    wm = get_workflow_manager()
    syncer = get_syncer()

    workflow = wm.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    visual_data = wm.to_visual_format(workflow_id)
    agents = [{"name": a.name, "description": a.description} for a in syncer.agents]

    return templates.TemplateResponse("workflow_run.html", {
        "request": request,
        "workflow": workflow,
        "workflow_json": json.dumps(visual_data),
        "agents": agents,
    })


@app.post("/api/workflows/{workflow_id}/execute")
async def execute_workflow(request: Request, workflow_id: str):
    """Start workflow execution."""
    global _workflow_runs
    wm = get_workflow_manager()

    workflow = wm.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    data = await request.json()
    user_prompt = data.get("prompt", "")

    # Create run ID
    run_id = str(uuid.uuid4())[:8]

    # Initialize run state
    _workflow_runs[run_id] = {
        "id": run_id,
        "workflow_id": workflow_id,
        "workflow_name": workflow.name,
        "status": "running",
        "prompt": user_prompt,
        "current_step": workflow.entry_point,
        "completed_steps": [],
        "step_outputs": {},
        "started_at": datetime.now().isoformat(),
        "finished_at": None,
        "error": None,
    }

    return {"success": True, "run_id": run_id}


@app.get("/api/workflows/runs/{run_id}")
async def get_workflow_run(run_id: str):
    """Get workflow run status."""
    if run_id not in _workflow_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    return _workflow_runs[run_id]


@app.post("/api/workflows/runs/{run_id}/step")
async def advance_workflow_step(request: Request, run_id: str):
    """Advance to next step in workflow (simulates agent completion)."""
    global _workflow_runs

    if run_id not in _workflow_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    run = _workflow_runs[run_id]
    if run["status"] != "running":
        return {"success": False, "error": "Workflow not running"}

    data = await request.json()
    step_output = data.get("output", "")
    next_step = data.get("next_step")

    wm = get_workflow_manager()
    workflow = wm.get_workflow(run["workflow_id"])

    if not workflow:
        run["status"] = "error"
        run["error"] = "Workflow not found"
        return {"success": False, "error": "Workflow not found"}

    # Record current step completion
    current_step = run["current_step"]
    if current_step:
        run["completed_steps"].append(current_step)
        run["step_outputs"][current_step] = step_output

    # Find next step
    if next_step:
        run["current_step"] = next_step
    else:
        # Auto-advance based on workflow edges
        visual = wm.to_visual_format(run["workflow_id"])
        next_steps = [e["to"] for e in visual["edges"] if e["from"] == current_step]

        if next_steps:
            run["current_step"] = next_steps[0]
        else:
            # No more steps - workflow complete
            run["current_step"] = None
            run["status"] = "completed"
            run["finished_at"] = datetime.now().isoformat()

    return {"success": True, "run": run}


@app.post("/api/workflows/runs/{run_id}/complete")
async def complete_workflow_run(request: Request, run_id: str):
    """Mark workflow run as complete."""
    global _workflow_runs

    if run_id not in _workflow_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    data = await request.json()
    run = _workflow_runs[run_id]
    run["status"] = data.get("status", "completed")
    run["finished_at"] = datetime.now().isoformat()
    if data.get("error"):
        run["error"] = data["error"]

    return {"success": True, "run": run}


@app.get("/api/workflows/runs/{run_id}/stream")
async def stream_workflow_run(run_id: str):
    """SSE endpoint for workflow run progress."""
    if run_id not in _workflow_runs:
        raise HTTPException(status_code=404, detail="Run not found")

    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            if run_id not in _workflow_runs:
                yield "data: {\"error\": \"Run not found\"}\n\n"
                break

            run = _workflow_runs[run_id]
            yield f"data: {json.dumps(run)}\n\n"

            if run["status"] in ["completed", "error", "cancelled"]:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# ============ Connections ============

@app.get("/connections", response_class=HTMLResponse)
async def connections_page(request: Request):
    """Connection monitor page."""
    cm = get_connection_monitor()
    status = cm.check_all_platforms()

    return templates.TemplateResponse("connections.html", {
        "request": request,
        "status": status,
        "platforms": status.platforms,
    })


@app.get("/api/connections/check")
async def check_all_connections():
    """Check all platform connections."""
    cm = get_connection_monitor()
    status = cm.check_all_platforms()
    return cm.to_dict(status)


@app.get("/api/connections/{platform_id}/check")
async def check_single_connection(platform_id: str):
    """Check single platform connection."""
    cm = get_connection_monitor()
    status = cm.check_platform(platform_id)

    return {
        "name": status.name,
        "cli_name": status.cli_name,
        "installed": status.installed,
        "cli_available": status.cli_available,
        "cli_version": status.cli_version,
        "config_exists": status.config_exists,
        "config_path": str(status.config_path) if status.config_path else None,
        "auth_status": status.auth_status,
        "auth_method": status.auth_method,
        "auth_details": status.auth_details,
        "last_checked": status.last_checked,
        "error": status.error,
        "fix_instructions": status.fix_instructions,
    }


# ============ Sync Progress (SSE) ============

@app.get("/sync/progress")
async def sync_progress():
    """Server-Sent Events endpoint for sync progress."""
    async def event_generator() -> AsyncGenerator[str, None]:
        while True:
            data = json.dumps(_sync_progress)
            yield f"data: {data}\n\n"
            if _sync_progress["status"] == "idle":
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# ============ API Endpoints ============

@app.get("/api/stats")
async def api_stats():
    """Get dashboard statistics as JSON."""
    syncer = get_syncer()
    em = get_exclusion_manager()

    return {
        "agents": {
            "total": len(syncer.agents),
            "excluded": len([a for a in syncer.agents if em.is_excluded("agent", a.name)])
        },
        "skills": {
            "total": len(syncer.skills),
            "excluded": len([s for s in syncer.skills if em.is_excluded("skill", s.name)])
        },
        "plugins": {
            "total": len(syncer.plugins),
            "excluded": len([p for p in syncer.plugins if em.is_excluded("plugin", p.name)])
        },
        "commands": {
            "total": len(syncer.commands),
            "excluded": len([c for c in syncer.commands if em.is_excluded("command", c.name)])
        },
        "hooks": {
            "total": len(syncer.hooks)
        }
    }


@app.get("/api/exclusions")
async def api_exclusions():
    """Get exclusion rules as JSON."""
    em = get_exclusion_manager()
    return em.export_rules()


def run_server(host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True):
    """Run the web server."""
    import uvicorn

    if open_browser:
        webbrowser.open(f"http://{host}:{port}")

    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
