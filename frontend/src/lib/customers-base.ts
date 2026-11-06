import { usePathname } from "next/navigation";

/** Customer pages are reachable from CRM and from Sales; links stay in the
 *  section the user came from. */
export function useCustomersBase(): string {
  const pathname = usePathname() ?? "";
  return pathname.startsWith("/sales/") ? "/sales/customers" : "/crm/customers";
}
