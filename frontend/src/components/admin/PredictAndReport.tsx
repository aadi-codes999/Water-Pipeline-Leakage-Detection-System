import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api from "@/api/api";
import { toast } from "sonner";
import Loader from "@/components/Loader";

const PredictAndReport = () => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [predictions, setPredictions] = useState<any[]>([]);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setFile(f);
  };

  const runPredict = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return toast.error("Select a CSV file to predict");
    setLoading(true);
    const form = new FormData();
    form.append("file", file);
    try {
      const resp = await api.post("/predict", form, { headers: { "Content-Type": "multipart/form-data" } });
      setPredictions(resp.data.predictions || []);
      toast.success("Prediction completed");
    } catch (err: any) {
      toast.error(err.response?.data?.error || "Prediction failed");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const sendSampleReport = async () => {
    const sample = { leaks: [{ zone_id: "Z-1", timestamp: new Date().toISOString(), description: "Sample leak" }] };
    try {
      const resp = await api.post("/report_leak", sample);
      toast.success(resp.data.message || "Report sent");
    } catch (err: any) {
      toast.error(err.response?.data?.error || "Report failed");
    }
  };

  return (
    <div className="space-y-6">
      <Card className="dashboard-section">
        <div className="flex items-start gap-4 mb-4">
          <div>
            <h2 className="text-2xl font-bold">Predict from CSV</h2>
            <p className="text-sm text-muted-foreground">Upload a CSV to run leak predictions using the server model</p>
          </div>
        </div>

        <form onSubmit={runPredict} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="predict-file">CSV File</Label>
            <Input id="predict-file" type="file" accept=".csv" onChange={handleFile} className="mt-2" />
            <p className="text-xs text-muted-foreground">
              Required columns: water_supplied_litres, water_consumed_litres, flowrate_lps, pressure_psi
            </p>
            <div className="text-xs bg-muted p-3 rounded">
              <p className="font-medium mb-1">Example CSV format:</p>
              <pre className="overflow-x-auto">
                water_supplied_litres,water_consumed_litres,flowrate_lps,pressure_psi
                1000,950,2.5,45
                1200,1150,2.8,42
              </pre>
            </div>
          </div>

          <Button type="submit" className="water-gradient w-full" disabled={loading || !file}>
            {loading ? "Predicting..." : "Run Prediction"}
          </Button>
        </form>

        <div className="mt-4">
          <h3 className="text-lg font-semibold mb-2">Predictions</h3>
          {predictions.length === 0 ? (
            <div className="text-muted-foreground">No predictions yet</div>
          ) : (
            <div className="text-xs bg-background p-3 rounded overflow-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left border-b">
                    {Object.keys(predictions[0]).map(key => (
                      <th key={key} className="p-2">{key}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {predictions.map((pred, idx) => (
                    <tr key={idx} className="border-b">
                      {Object.values(pred).map((val: any, i) => (
                        <td key={i} className="p-2">
                          {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-2">Quick Report</h3>
          <p className="text-sm text-muted-foreground">Send a sample leak report to the backend (uses /report_leak)</p>
          <div className="mt-2">
            <Button onClick={sendSampleReport} variant="outline">Send Sample Report</Button>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default PredictAndReport;
