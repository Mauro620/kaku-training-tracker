import { DetallePlanScreen } from "@/components/entreno/detalle-plan-screen";

type Params = Promise<{ id: string }>;

export default async function PlanDetallePage({ params }: { params: Params }) {
  const { id } = await params;
  return <DetallePlanScreen planId={Number(id)} />;
}
