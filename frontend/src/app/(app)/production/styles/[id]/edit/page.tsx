"use client";
import { useParams } from "next/navigation";
import { StyleForm } from "../../_style-form";

export default function EditStylePage() {
  const { id } = useParams<{ id: string }>();
  return <StyleForm styleId={id} />;
}
