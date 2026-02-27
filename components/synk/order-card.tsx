"use client"

import type { Order } from "@/lib/synk/types"
import { Badge } from "@/components/ui/badge"
import { Package, Calendar, DollarSign, Hash } from "lucide-react"

interface OrderCardProps {
  order: Order
  editable?: boolean
  onOrderChange?: (order: Order) => void
}

export function OrderCard({ order, editable = false, onOrderChange }: OrderCardProps) {
  const handleChange = (field: keyof Order, value: string | number) => {
    if (onOrderChange) {
      onOrderChange({ ...order, [field]: value })
    }
  }

  const fields = [
    {
      icon: Package,
      label: "Product",
      value: order.product,
      field: "product" as keyof Order,
      type: "text",
    },
    {
      icon: Hash,
      label: "Quantity",
      value: order.quantity,
      field: "quantity" as keyof Order,
      type: "number",
    },
    {
      icon: DollarSign,
      label: "Price/Unit",
      value: order.requestedPrice,
      field: "requestedPrice" as keyof Order,
      type: "number",
    },
    {
      icon: Calendar,
      label: "Delivery Days",
      value: order.requestedDeliveryDays,
      field: "requestedDeliveryDays" as keyof Order,
      type: "number",
    },
  ]

  return (
    <div className="rounded-xl border border-border bg-card p-4 animate-float-in shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-muted-foreground">{order.id}</span>
          <Badge variant="outline" className="text-[10px] border-[var(--agent-sales)] text-[var(--agent-sales)]">
            {order.priority.toUpperCase()}
          </Badge>
        </div>
        <span className="text-xs text-muted-foreground">{order.customer}</span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {fields.map(({ icon: Icon, label, value, field, type }) => (
          <div key={field} className="flex items-center gap-2 px-2.5 py-2 rounded-lg bg-secondary/50">
            <Icon className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
            <div className="flex flex-col min-w-0">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wide">{label}</span>
              {editable ? (
                <input
                  type={type}
                  value={value}
                  onChange={(e) =>
                    handleChange(
                      field,
                      type === "number" ? parseFloat(e.target.value) || 0 : e.target.value
                    )
                  }
                  className="bg-transparent text-sm font-mono text-foreground outline-none w-full border-b border-dashed border-muted-foreground/30 focus:border-primary"
                />
              ) : (
                <span className="text-sm font-mono text-foreground">
                  {typeof value === "number" && field === "requestedPrice"
                    ? `$${value.toFixed(2)}`
                    : typeof value === "number"
                      ? value.toLocaleString()
                      : value}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
