import { CicloDetalleCliente } from "./_ciclo-detalle-cliente";

/**
 * Server component. Next 15 obliga a este layer para resolver el
 * parametro dinamico como Promise (compatible con React Server
 * Components y con la generacion estatica de paginas que el [id] no
 * tiene: la lista de ids la da el server, no es enumerable).
 */
export default async function CicloDetallePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const cicloId = Number(id);
  return <CicloDetalleCliente cicloId={cicloId} />;
}
