import { useEffect, useRef, useState } from "react";
import { instance } from "@viz-js/viz";
import { Box, Button, Dialog, DialogActions, DialogContent, DialogTitle, Typography } from "@mui/material";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  dot: string;
}

export default function RouteGraphModal({ isOpen, onClose, dot }: Props) {
  const graphContainerRef = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    async function render() {
      if (!isOpen || !dot) return;
      try {
        setError("");
        const viz = await instance();
        const svgElement = viz.renderSVGElement(dot);
        if (!cancelled && graphContainerRef.current) {
          graphContainerRef.current.innerHTML = "";
          graphContainerRef.current.appendChild(svgElement);
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
    <Dialog open={isOpen} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>Course Route Graph</DialogTitle>
      <DialogContent dividers>
        {error ? (
          <Typography color="error">{error}</Typography>
        ) : (
          <Box
            ref={graphContainerRef}
            sx={{
              overflow: "auto",
              "& svg": {
                width: "100%",
                height: "auto",
                minWidth: 640,
              },
            }}
          />
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
