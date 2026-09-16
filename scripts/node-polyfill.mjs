// SingleFile CLI (via simple-cdp) expects a CloseEvent global, which Node < 23 lacks.
// Without it the CLI crashes and leaves an empty file. Loaded via NODE_OPTIONS in capture.py.
if (typeof globalThis.CloseEvent === "undefined") {
  globalThis.CloseEvent = class CloseEvent extends Event {
    constructor(type, init = {}) { super(type, init); this.code = init.code ?? 0; this.reason = init.reason ?? ""; this.wasClean = init.wasClean ?? false; }
  };
}