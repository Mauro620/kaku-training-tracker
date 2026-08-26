import { DetalleSesionScreen } from "@/components/entreno/detalle-sesion-screen";

type Params = Promise<{ id: string }>;

export default async function SesionDetallePage({ params }: { params: Params }) {
  const { id } = await params;
  return <DetalleSesionScreen sesionId={id} />;
}
