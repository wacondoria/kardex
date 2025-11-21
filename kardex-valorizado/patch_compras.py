
import os

file_path = r"c:\Users\USER\Github\kardex\kardex-valorizado\src\views\compras_window.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find anchors
start_anchor_idx = -1
end_anchor_idx = -1

for i, line in enumerate(lines):
    if "def recalcular_totales(self):" in line:
        # Find the end of this method. It ends before the next def or weird block.
        # In the corrupted file, it seems to end around line 378 with det['subtotal'] = ...
        pass
    
    if "det['subtotal'] = float(sub_linea)" in line:
        # This is the last line of recalcular_totales loop
        start_anchor_idx = i + 1
    
    if "def detalle_editado(self, row, column):" in line:
        end_anchor_idx = i
        break

if start_anchor_idx != -1 and end_anchor_idx != -1:
    print(f"Found anchors: Start {start_anchor_idx}, End {end_anchor_idx}")
    
    # Construct new content
    new_content = []
    
    # 1. Keep everything up to start_anchor (inclusive of the last line of recalcular_totales)
    # But wait, the loop in recalcular_totales needs to be closed?
    # The code was:
    #             det['subtotal'] = float(sub_linea)
    # 
    #         self.lbl_subtotal.setText(f"{subtotal:,.2f}")
    #         self.lbl_igv.setText(f"{igv:,.2f}")
    #         self.lbl_total.setText(f"{total:,.2f}")
    
    # I need to check if those lines (lbl_subtotal...) are present in the corrupted file.
    # In Step 37, they were NOT visible after det['subtotal'].
    # Instead it went to `"""`.
    
    # So I need to restore the end of recalcular_totales too.
    
    # Let's look for "def recalcular_totales" again and find where it starts.
    recalc_idx = -1
    for i, line in enumerate(lines):
        if "def recalcular_totales(self):" in line:
            recalc_idx = i
            break
            
    if recalc_idx == -1:
        print("Could not find recalcular_totales")
        exit(1)
        
    # We will replace from recalcular_totales onwards to detalle_editado
    
    # New code for recalcular_totales + guardar_compra + producto_en_detalle_editado
    new_block = [
        "    def recalcular_totales(self):\n",
        "        subtotal = Decimal(0)\n",
        "        igv = Decimal(0)\n",
        "        total = Decimal(0)\n",
        "        \n",
        "        incluye_igv = self.chk_incluye_igv.isChecked()\n",
        "        \n",
        "        for det in self.detalles_compra:\n",
        "            cant = Decimal(str(det['cantidad']))\n",
        "            precio = Decimal(str(det['precio_unitario']))\n",
        "            \n",
        "            if incluye_igv:\n",
        "                # Precio incluye IGV\n",
        "                sub_linea = cant * precio\n",
        "                base_linea = sub_linea / Decimal('1.18')\n",
        "                igv_linea = sub_linea - base_linea\n",
        "            else:\n",
        "                # Precio mas IGV\n",
        "                base_linea = cant * precio\n",
        "                igv_linea = base_linea * Decimal('0.18')\n",
        "                sub_linea = base_linea + igv_linea\n",
        "                \n",
        "            subtotal += base_linea\n",
        "            igv += igv_linea\n",
        "            total += sub_linea\n",
        "            \n",
        "            # Actualizar subtotal en dict visual (aproximado)\n",
        "            det['subtotal'] = float(sub_linea)\n",
        "\n",
        "        self.lbl_subtotal.setText(f\"{subtotal:,.2f}\")\n",
        "        self.lbl_igv.setText(f\"{igv:,.2f}\")\n",
        "        self.lbl_total.setText(f\"{total:,.2f}\")\n",
        "\n",
        "    def guardar_compra(self):\n",
        "        if not self.detalles_compra:\n",
        "            QMessageBox.warning(self, \"Error\", \"Debe agregar al menos un producto.\")\n",
        "            return\n",
        "            \n",
        "        try:\n",
        "            # 1. Preparar datos de cabecera\n",
        "            datos_cabecera = {\n",
        "                'proveedor_id': self.cmb_proveedor.currentData(),\n",
        "                'fecha': self.date_fecha.date().toPyDate(),\n",
        "                'fecha_registro_contable': self.date_fecha_contable.date().toPyDate(),\n",
        "                'tipo_documento': self.cmb_tipo_doc.currentText(),\n",
        "                'numero_documento': self.txt_numero_doc.text(),\n",
        "                'moneda': self.cmb_moneda.currentData(),\n",
        "                'tipo_cambio': Decimal(str(self.spn_tc.value())),\n",
        "                'incluye_igv': self.chk_incluye_igv.isChecked(),\n",
        "                'observaciones': self.txt_observaciones.toPlainText(),\n",
        "            }\n",
        "            \n",
        "            # 2. Preparar detalles\n",
        "            # self.detalles_compra ya es una lista de dicts compatible\n",
        "            \n",
        "            # 3. Llamar al manager\n",
        "            compra_id = self.compra_a_editar.id if self.compra_a_editar else None\n",
        "            \n",
        "            # Asegurar que el manager existe\n",
        "            if not hasattr(self, 'compras_manager'):\n",
        "                 from utils.compras_manager import ComprasManager\n",
        "                 self.compras_manager = ComprasManager(self.session)\n",
        "            \n",
        "            self.compras_manager.guardar_compra(datos_cabecera, self.detalles_compra, compra_id=compra_id)\n",
        "            \n",
        "            self.accept()\n",
        "            \n",
        "        except Exception as e:\n",
        "            self.session.rollback()\n",
        "            import traceback\n",
        "            traceback.print_exc()\n",
        "            QMessageBox.critical(self, \"Error\", f\"Error al guardar: {e}\")\n",
        "\n",
        "    def producto_en_detalle_editado(self, combo_index, row):\n",
        "        \"\"\"\n",
        "        Maneja el cambio de un producto en el ComboBox de la tabla de detalles.\n",
        "        \"\"\"\n",
        "        if 0 <= row < len(self.detalles_compra):\n",
        "            combo_box = self.tabla_productos.cellWidget(row, 0)\n",
        "            if not combo_box:\n",
        "                return\n",
        "\n",
        "            nuevo_producto_id = combo_box.itemData(combo_index)\n",
        "            nuevo_producto_nombre = combo_box.itemText(combo_index)\n",
        "\n",
        "            if nuevo_producto_id is not None:\n",
        "                detalle_actualizado = self.detalles_compra[row]\n",
        "                detalle_actualizado['producto_id'] = nuevo_producto_id\n",
        "                detalle_actualizado['producto_nombre'] = nuevo_producto_nombre\n",
        "            else:\n",
        "                print(f\"ADVERTENCIA: No se pudo obtener el ID del producto para el índice {combo_index} en la fila {row}\")\n",
        "\n"
    ]
    
    final_lines = lines[:recalc_idx] + new_block + lines[end_anchor_idx:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(final_lines)
        
    print("File patched successfully.")

else:
    print("Could not find anchors.")
