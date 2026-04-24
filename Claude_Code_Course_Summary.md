# Claude Code - Full Course Summary (101 + Claude Code in Action)

Combined summary of both Claude Code courses. Read this before every
Claude Code session on the Retina Advisors project.

---

## 1. What Claude Code Actually Is

Claude Code is not a chat interface. It is a terminal-based coding
assistant that lives directly inside your development environment. The
key difference from Claude.ai is that it can take real actions - read
and write files, run terminal commands, install packages, commit to
git, and operate autonomously on your codebase.

**The tool use foundation:**
Language models by themselves can only process text and return text.
They cannot read files or run commands on their own. Claude Code solves
this with tool use - it adds instructions to your prompt that teach
Claude how to request actions. When Claude wants to read a file, it
formats a response saying so, Claude Code intercepts that, reads the
actual file, and sends the contents back. This loop is invisible to
you but it is happening on every meaningful interaction.

**Why Claude's tool use matters here:**
Not all models use tools equally well. Claude is specifically strong at
understanding what tools do and combining them to handle complex tasks.
This is why Claude Code can navigate a codebase without indexing your
entire project to an external server - it reads only what it needs,
when it needs it.

**The fraud analogy:**
Tool use is how Claude Code is like a fraud analyst with system access
rather than a consultant reading a report. The consultant can only work
with what you hand them. The analyst with system access can pull the
transaction record, check the account history, run the query - all
on their own. Claude Code has that kind of access to your codebase.

---

## 2. The CLAUDE.md File - Persistent Memory

CLAUDE.md is the single most important concept in Claude Code. Without
it, every session starts from scratch - Claude has to re-explore your
codebase, re-learn your conventions, and re-discover what you have
already built. With it, Claude Code reads your project context
automatically every time you open a session.

**Think of it as an onboarding script for your codebase.** Every
instruction in CLAUDE.md gets appended to your prompt on every
request - like a persistent system prompt that never leaves.

**Three locations, three purposes:**

Project-level CLAUDE.md - lives in the root directory, committed to
git, shared with your whole team. This is the one we built for the
Retina Advisors project.

CLAUDE.local.md - lives in your project directory but is not committed
to git. Personal instructions that apply only to you on this machine.

~/.claude/CLAUDE.md - applies to every project on your machine. Put
personal preferences here that you always want regardless of project.

**What belongs in CLAUDE.md:**
- Your tech stack and architecture
- Key commands (how to start the dev server, run tests, etc.)
- Code style preferences
- Hard rules that must always be enforced
- File paths that are always relevant

**What does not belong in CLAUDE.md:**
- Everything. Keep it lean. The more bloated it gets, the more tokens
  it burns on every single request. Only the things Claude would
  otherwise have to re-discover every session.

**The # command:**
Type # in Claude Code to enter memory mode. Claude will merge whatever
you type directly into your CLAUDE.md file. Use this to save
corrections you find yourself making repeatedly - instead of
re-correcting Claude every session, save the correction once and it
will know going forward.

**Referencing files in CLAUDE.md:**
Use @ syntax to point Claude at specific files:
  The database schema is defined in @prisma/schema.prisma.
  Reference it anytime you need to understand the data structure.

That file's contents will be included in every request automatically.

---

## 3. The /init Command

When you open a new project in Claude Code for the first time, run
/init before doing anything else. This command tells Claude to scan
your entire codebase and understand: the project purpose, the
architecture, the important commands, the coding patterns.

After analyzing, Claude creates a CLAUDE.md file automatically. This
is your starting point - not a replacement for the intentional CLAUDE.md
we built for this project, but a useful baseline Claude generates by
reading what actually exists.

For the Retina Advisors project: when we open Claude Code, we will
already have our CLAUDE.md built. We will move it into the repo before
running /init, so Claude reads our intentional rules rather than
generating generic ones from scratch.

---

## 4. Context Management - The Most Underrated Skill

Context is Claude's working memory. Every file it reads, every command
it runs, every message you send - it all accumulates in the context
window. There is a finite amount of space, and when it fills up,
things get lost.

**This is the primary failure mode in long Claude Code sessions.**
Not bad prompts. Not wrong tools. Context pressure - Claude forgetting
things it knew an hour ago because the window is full.

**The two commands:**

/compact - summarizes your conversation history while keeping important
context. Use this when you are deep in a feature and running out of
space but want Claude to remember what it has learned about your
codebase so far.

/clear - wipes everything and starts fresh. Use this when you switch
to a completely different task. Old context from a different feature
introduces bias into something new.

The rule: /compact to continue, /clear to restart.

**Tips for protecting your context window:**

Be specific in prompts. A vague prompt seems smaller but costs more -
Claude has to explore more to fill in the gaps you left. A detailed
prompt costs tokens upfront but saves much more downstream.

Manage MCP servers. Every MCP server you have configured loads all its
tools into context by default, even when you are not using them. On
the Retina Advisors project, when you do not need the Stripe MCP
active, turn it off. Tools you are not using are just burning context.

Use subagents. Subagents run in a completely separate context window.
For tasks where you only need the answer - not the journey - delegate
to a subagent and get back just the summary.

**The /context command:**
Run /context at any time to see a breakdown of what is eating your
context window. Categories, sizes, visual graphic. Use it before you
hit the wall, not after.

---

## 5. The Explore - Plan - Code - Commit Workflow

This is the single most important workflow pattern in the courses. Most
people skip straight to Code. That is why most Claude Code sessions
produce more course-correcting than actual progress.

**Explore:**
Before writing any code, give Claude the relevant context. Ask it to
read the files that matter. Use @ mentions to pull in specific files.
Run the explore subagent if you want a general summary of the codebase.
The goal is making sure Claude knows what already exists before
building anything new.

**Plan:**
Enable Plan Mode by pressing Shift + Tab. In Plan Mode, Claude cannot
edit files - it can only read. Give Claude the task and ask it to
produce a plan without writing any code yet. Claude will read relevant
files, run searches, and give you a step-by-step approach.

This is the best place to course-correct. It is before any code is
written. Review the plan, ask for revisions if it missed something,
make sure the success criteria is explicit. Claude needs to know what
"correct" looks like before it starts.

**Code:**
Once the plan is approved, press "approve" and let Claude work. You
can choose whether Claude auto-accepts file edits or asks you each
time. Claude will troubleshoot before calling anything finished. If
it keeps running into the same issue, ask it to save the solution to
CLAUDE.md so it does not repeat the mistake next session.

**Commit:**
Before pushing anything, run a subagent code reviewer. Subagents get
fresh eyes - they do not carry the bias of the main agent that just
spent an hour writing the code. Restrict the reviewer subagent to
read-only tools. A reviewer should flag issues, not change files.

Then use /commit-push-pr to handle the commit, push, and PR creation
in one step.

**The fraud analogy:**
Explore = case intake, understand what you are working with.
Plan = investigation strategy, decide approach before acting.
Code = work the case.
Commit = file the report.
Skipping Plan and going straight to Code is like a fraud analyst
opening disputes without reading the account first.

---

## 6. Subagents - Parallel Context Windows

Subagents are separate instances of Claude Code that run in parallel
with their own isolated context windows. They do a task, summarize
the result, and return just the summary to your main agent.

**Why this matters:**
A lot of context window gets consumed by the exploration and reasoning
needed to answer a question - tool calls, file reads, web searches.
That journey is not always something you need to keep. When you only
need the answer, a subagent handles the journey in its own window
and hands you the result. Your main context stays clean.

**Code review subagent:**
Before every commit, ask Claude to spawn a subagent to review the
changes. The subagent has no memory of writing that code - it reviews
with genuinely fresh eyes. Restrict it to read-only tools.

**Creating a subagent:**
Run /agents in Claude Code, then select "Create new agent." Claude
walks you through defining the agent's purpose, tools it can access,
and when it should be invoked automatically.

Subagents are defined in Markdown files with YAML frontmatter. They
can have persistent memory across conversations and preloaded skills.

---

## 7. Hooks - Deterministic Enforcement

Hooks are the most important concept that most people miss entirely.
Everything else in Claude Code is probabilistic - you can tell Claude
in CLAUDE.md to always format files after editing, and most of the
time it will. But sometimes it will not.

**Hooks always run. No exceptions.**

A hook is a command you configure to execute at a specific point in
Claude Code's lifecycle. If you need something to happen every time
without fail, put it in a hook - not in a prompt.

**The two primary hook types:**

PreToolUse - runs before a tool call executes. Can inspect the proposed
action and block it by exiting with code 2. Claude receives your
error message and understands why it was blocked.

PostToolUse - runs after a tool call completes. Cannot block but can
run follow-up actions like formatting a file that was just edited or
running tests after a change.

**Hook configuration lives in settings files:**
- ~/.claude/settings.json - applies to all your projects
- .claude/settings.json - project level, committed to git, shared
- .claude/settings.local.json - project level, not committed, personal

**A practical PreToolUse hook example:**
Block Claude from reading .env files during development:

```json
"PreToolUse": [
  {
    "matcher": "Read|Grep",
    "hooks": [
      {
        "type": "command",
        "command": "node ./hooks/read_hook.js"
      }
    ]
  }
]
```

The hook script reads JSON from stdin describing the proposed tool
call, checks if the file path contains .env, and exits with code 2
to block it. Claude sees your error message and understands.

**A practical PostToolUse hook example:**
Auto-format after every file edit:

```json
"PostToolUse": [
  {
    "matcher": "Write|Edit|MultiEdit",
    "hooks": [
      {
        "type": "command",
        "command": "node ./hooks/format_hook.js"
      }
    ]
  }
]
```

**The full list of hook events:**
PreToolUse, PostToolUse, Notification, Stop, SubagentStop,
PreCompact, UserPromptSubmit, SessionStart, SessionEnd

**Important:** The JSON data your hook receives via stdin differs
by hook type AND by which tool triggered it. Before writing a real
hook, use this debug configuration to capture exactly what data
you will receive:

```json
"PostToolUse": [
  {
    "matcher": "*",
    "hooks": [
      {
        "type": "command",
        "command": "jq . > post-log.json"
      }
    ]
  }
]
```

This writes the raw input to a file so you can see the exact
structure before building your logic.

**Sharing hooks with your team:**
Hooks in .claude/settings.json are project-level and commit to your
repo. Your whole team gets them automatically. Use the
CLAUDE_PROJECT_DIR environment variable to reference scripts stored
in the project so paths work on any machine.

**For the Retina Advisors project:**
Hooks we should add:
- PostToolUse to run tests after any Python file edit
- PreToolUse to block writes to production config files
- PostToolUse to enforce code formatting

---

## 8. Conversation Control - Escape, Rewind, Redirect

**Escape key:**
Stops Claude mid-response. Use this when Claude starts heading the
wrong direction or tries to do too much at once. Press Escape, redirect
with a more specific prompt. Do not let Claude keep going on a wrong
path - stopping early is cheaper than course-correcting after.

**Double Escape - conversation rewind:**
Press Escape twice to see all messages you have sent. Select an
earlier point and continue from there. This removes subsequent context
without losing what Claude learned before that point. Use it when a
debugging rabbit hole has cluttered your conversation but Claude's
understanding of your codebase is still valuable.

**Combining Escape with CLAUDE.md:**
When Claude makes the same mistake repeatedly across sessions:
1. Press Escape to stop the current response
2. Use the # shortcut to save the correct approach to CLAUDE.md
3. Continue with the corrected instruction in memory

This converts a recurring correction into a permanent rule.

---

## 9. Custom Commands

You can create your own /commands that Claude Code runs on demand.
Commands are Markdown files stored in .claude/commands/.

The filename becomes the command name: audit.md creates /audit.

**Commands with arguments:**
Use the $ARGUMENTS placeholder in your command file:

```
Write comprehensive tests for: $ARGUMENTS
Testing conventions:
- Use Vitest with React Testing Library
- Place test files in __tests__ directory
- Name files [filename].test.ts(x)
```

Run it as: /write_tests the use-auth.ts file in the hooks directory

**What belongs in custom commands:**
Repetitive workflows that need to be consistent every time. Running
a specific test suite. Generating boilerplate following your team's
conventions. Deploying to a specific environment.

**After creating a command file, restart Claude Code** for it to
recognize the new command.

---

## 10. MCP Servers in Claude Code

Adding an MCP server to Claude Code:

```
claude mcp add [server-name] [command-to-start-server]
```

Example - adding the Playwright browser control server:

```
claude mcp add playwright npx @playwright/mcp@latest
```

Claude Code connects automatically on startup. To pre-approve
permissions so Claude does not ask every time, add to
.claude/settings.local.json:

```json
{
  "permissions": {
    "allow": ["mcp__playwright"],
    "deny": []
  }
}
```

Note the double underscore in mcp__playwright.

**For the Retina Advisors project:**
The Stripe MCP server and our custom delivery MCP server get added
this way. Once registered, Claude Code connects to them automatically
and can use their tools without any additional configuration.

**Context cost reminder:**
Every MCP server loads all its tools into context by default. If you
have servers configured that are not relevant to the current task,
turn them off. Only run the servers you actually need for what you are
building right now.

---

## 11. The Claude Code SDK - Running Claude Programmatically

The SDK lets you run Claude Code from within your own scripts and
applications. This is how the query duplication hook works - it
launches a second Claude Code instance to review changes made by the
first.

**Basic TypeScript usage:**

```typescript
import { query } from "@anthropic-ai/claude-code";

for await (const message of query({
  prompt: "Look for duplicate queries in the ./src/queries dir",
})) {
  console.log(JSON.stringify(message, null, 2));
}
```

Default permissions are read-only. To enable writes:

```typescript
for await (const message of query({
  prompt: "Fix the duplicate query",
  options: {
    allowedTools: ["Edit"]
  }
})) {
  console.log(JSON.stringify(message, null, 2));
}
```

**Where the SDK matters for this project:**
The evaluator-optimizer loop in our prompt architecture is conceptually
similar to the SDK pattern - one Claude instance producing output,
another reviewing it. Understanding the SDK gives you the mental model
for how that loop works even if we implement it differently in Python.

---

## 12. GitHub Integration

Set up with /install-github-app in Claude Code. This creates two
GitHub Actions:

**Mention action:** @claude in any issue or PR. Claude analyzes the
request, creates a task plan, executes it with full codebase access,
and posts results.

**PR review action:** Every new PR automatically gets reviewed by
Claude. Changes analyzed, impact assessed, report posted.

**Permissions in GitHub Actions:**
Unlike local development, there is no shortcut. Every tool from every
MCP server must be individually listed in allowed_tools:

```yaml
allowed_tools: "Bash(npm:*),mcp__playwright__browser_snapshot,..."
```

---

## Key Principles for the Retina Advisors Build

**From the courses, applied to our specific situation:**

CLAUDE.md is already built. Move it into the repo before anything
else. This is the first file that goes in.

Use Plan Mode for every feature. The dispute analyzer has multiple
interconnected components - parallelization, MCP connections, the
evaluator loop. Plan before touching any of them.

Set up hooks early. Auto-formatting and test-running after file edits
should be configured on day one, not retrofitted after the build is
messy. Same philosophy as setting temperature 0.1 from the first API
call - establish the right defaults before you have anything to lose.

Subagent code review before every commit. This is non-negotiable given
that a hiring manager is the target audience. No sloppy commits.

/clear between major features. Building the custom MCP server is a
completely different task from building the parallelization layer.
Start each major component with clean context.

Context awareness on MCP servers. We will have Stripe MCP and our
custom delivery MCP both configured. When working on one, turn off
the other. Do not burn context on tools you are not currently using.

The # command is your escape valve. Every time you catch yourself
correcting Claude on something it should already know, save it to
CLAUDE.md immediately with #. Convert corrections into rules.
