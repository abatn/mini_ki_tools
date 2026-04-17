import React, { useState, useEffect } from 'react';

const DebuggerPanel = ({
  isDebugging,
  currentLine,
  currentFile,
  variables,
  callStack,
  onStepOver,
  onStepInto,
  onStepOut,
  onResume,
  onPause,
  onBreakpointToggle
}) => {
  const [isRunning, setIsRunning] = useState(false);
  const [debugInfo, setDebugInfo] = useState({
    currentLine: 0,
    currentFile: '',
    variables: [],
    callStack: []
  });

  useEffect(() => {
    if (isDebugging) {
      setDebugInfo({
        currentLine,
        currentFile,
        variables,
        callStack
      });
    }
  }, [isDebugging, currentLine, currentFile, variables, callStack]);

  const handleStepOver = () => {
    onStepOver && onStepOver();
  };

  const handleStepInto = () => {
    onStepInto && onStepInto();
  };

  const handleStepOut = () => {
    onStepOut && onStepOut();
  };

  const handleResume = () => {
    onResume && onResume();
  };

  const handlePause = () => {
    onPause && onPause();
  };

  const handleBreakpointToggle = (lineNumber) => {
    onBreakpointToggle && onBreakpointToggle(lineNumber);
  };

  if (!isDebugging) {
    return null;
  }

  return (
    <div className="debugger-panel">
      <div className="debugger-header">
        <h3>Debugger</h3>
        <div className="debugger-controls">
          <button onClick={handleStepOver} title="Step Over">➡️</button>
          <button onClick={handleStepInto} title="Step Into">⏬</button>
          <button onClick={handleStepOut} title="Step Out">⏫</button>
          <button onClick={handleResume} title="Resume">▶️</button>
          <button onClick={handlePause} title="Pause">⏸️</button>
        </div>
      </div>

      <div className="debugger-content">
        <div className="debugger-location">
          <span>Line {currentLine} in {currentFile}</span>
        </div>

        <div className="debugger-variables">
          <h4>Variables</h4>
          <ul>
            {variables.map((variable, index) => (
              <li key={index}>
                <strong>{variable.name}:</strong> {variable.value}
              </li>
            ))}
          </ul>
        </div>

        <div className="debugger-callstack">
          <h4>Call Stack</h4>
          <ul>
            {callStack.map((frame, index) => (
              <li key={index}>
                {frame.function} in {frame.file}:{frame.line}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default DebuggerPanel;