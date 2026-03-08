import { useEffect, useState } from "react";
import { instance } from "@viz-js/viz";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  dot: string;
}

export default function RouteGraphModal({ isOpen, onClose, dot }: Props) {
  const [svgMarkup, setSvgMarkup] = useState<string>("");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    async function render() {
      if (!isOpen || !dot) return;
      try {
        setError("");
        const viz = await instance();
        const svg = viz.renderString(dot);
        if (!cancelled) {
          setSvgMarkup(svg);
        }
      } catch (e) {
        if (!cancelled) {
          setError(`Could not render graph: ${String(e)}`);
        }
      }
    }
    render();
    return () => {
      cancelled = true;
    };
  }, [isOpen, dot]);

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop">
      <div className="modal-card">
        <div className="modal-header">
          <h3>Course Route Graph</h3>
          <button onClick={onClose}>Close</button>
        </div>
        {error ? (
          <p className="error-text">{error}</p>
        ) : (
          <div className="graph-area" dangerouslySetInnerHTML={{ __html: svgMarkup }} />
        )}
      </div>
    </div>
  );
}
