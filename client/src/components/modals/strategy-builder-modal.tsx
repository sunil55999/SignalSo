import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface StrategyBuilderModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function StrategyBuilderModal({ isOpen, onClose }: StrategyBuilderModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-hidden">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold text-dark">
            Visual Strategy Builder
          </DialogTitle>
        </DialogHeader>
        
        <div className="p-6 h-96">
          <div className="h-full bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 flex items-center justify-center">
            <div className="text-center">
              <i className="fas fa-project-diagram text-4xl text-gray-400 mb-4"></i>
              <p className="text-gray-500 font-medium">React Flow Strategy Builder</p>
              <p className="text-sm text-gray-400 mb-4">
                Drag and drop logic blocks to create trading strategies
              </p>
              <div className="text-xs text-gray-400 space-y-1">
                <p>• IF Confidence &lt; 70% → Skip Trade</p>
                <p>• IF TP1 Hit → Move SL to Entry</p>
                <p>• IF Market Hours → Enable Trading</p>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
