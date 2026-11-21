// Dialogue-only Command Code endpoint. No shell, file, MCP or delegation tool.
// Loaded explicitly per invocation; never installed into the user's global config.
export default function (cmd) {
  cmd.on('session_start', () => {
    cmd.setActiveTools([]);
    if (cmd.getActiveTools().length === 0) {
      process.stderr.write('STACK_AGENT_LINK_TOOLS_NONE\n');
    }
  });
  cmd.hooks({
    beforeToolCall: () => ({
      block: true,
      terminate: true,
      additionalContext: 'Agent Link is dialogue-only. Host actions require the pinned allowlist.',
    }),
  });
}
