- re-work python to use more rich's features
- separate out the configuration and the build tree so that they can be
    cleaned easily
# Bugs
After adding a new ref to the sources list I get this.
> [!BUG] Fetch when there is an unknown ref
> ```
GitCommandError: Cmd('C:\Program Files\Git\bin\git.exe') failed due to: exit code(128)
  cmdline: C:\Program Files\Git\bin\git.exe rev-parse tracy-shared
  stdout: 'tracy-shared'
  stderr: 'fatal: ambiguous argument 'tracy-shared': unknown revision or path not in the working tree.
Use '--' to separate paths from revisions, like this:
'git <command> [<revision>...] -- [<file>...]''
git rev-parse local tracy-shared
> ```

I had AI fix it on the mac, but I'm not on the mac now.
I don't know what my working directory is to test.

it's in the fetch code so lets look at that again.

I didn't like that the git fetch was in the built_utils and not the git_utils, and there was also a shim which conditionally ran based on whether dry run was specified.
So I moved it, and fixed up the references.
So far so good, the error remains as its the same problem.

I am noticing a bunch of shitty code, man I was really moving fast when I built this thing.

I am in the process of splitting it up into smaller pieces so that its easier to parse and fix.

I'm also going to try to remove the abuse of exceptions for control flow.

Well it seems that the gitpython is a simple wrapper over git and so using exceptions is how it operates. but it is not normal control flow in python.
I am going to create wrappers around the git commands that throw.

Also as an aside, my local LLM is unable to perform even the most basic response on a short function inside of clion because it probably does too much.
it works fine in the web interface. so its probably differences in the tools. I wonder if i can expose clion mcp to the llama interface.

I really worked hard on the fetching code. not sure all the changes were worth the trouble, 

> [!BUG] git log
> ```
> ┌─────────────────────────────────── Error ───────────────────────────────────┐
│ GitCommandError: Cmd('C:\Program Files\Git\bin\git.exe') failed due to:     │
│ exit code(128)                                                              │
│   cmdline: C:\Program Files\Git\bin\git.exe log --format=%h -1              │
│ enetheru/tracy-shared                                                       │
│   stderr: 'fatal: ambiguous argument 'enetheru/tracy-shared': unknown       │
│ revision or path not in the working tree.                                   │
│ Use '--' to separate paths from revisions, like this:                       │
│ 'git <command> [<revision>...] -- [<file>...]''                             │
│ git log bare pattern=enetheru/tracy-shared                                  │
└─────────────────────────────────────────────────────────────────────────────┘
> ```

