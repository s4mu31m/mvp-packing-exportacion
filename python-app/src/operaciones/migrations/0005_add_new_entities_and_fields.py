"""
Agrega campos extendidos a Bin/Lote/Pallet y crea los 9 modelos nuevos
del flujo operativo: CamaraMantencion, Desverdizado, CalidadDesverdizado,
IngresoAPacking, RegistroPacking, ControlProcesoPacking, CalidadPallet,
CamaraFrio, MedicionTemperaturaSalida.
"""

import django.db.models.deletion
from django.db import migrations, models


TIPO_EVENTO_CHOICES = [
    ('BIN_REGISTRADO', 'Bin registrado'),
    ('LOTE_CREADO', 'Lote creado'),
    ('PALLET_CREADO', 'Pallet creado'),
    ('LOTE_ASIGNADO_PALLET', 'Lote asignado a pallet'),
    ('PALLET_CERRADO', 'Pallet cerrado'),
    ('PESAJE', 'Pesaje y asignacion de lote'),
    ('DESVERDIZADO_INGRESO', 'Ingreso a desverdizado'),
    ('DESVERDIZADO_SALIDA', 'Salida de desverdizado'),
    ('CAMARA_MANTENCION', 'Ingreso a camara de mantencion'),
    ('CAMARA_MANTENCION_SALIDA', 'Salida de camara de mantencion'),
    ('PACKING_PROCESO', 'Proceso de packing'),
    ('CONTROL_CALIDAD', 'Control de calidad'),
    ('INGRESO_PACKING', 'Ingreso a proceso de packing'),
    ('CAMARA_FRIO_INGRESO', 'Ingreso a camara de frio'),
    ('CONTROL_TEMPERATURA', 'Control de temperatura en camara'),
    ('CALIDAD_DESVERDIZADO', 'Control de calidad posterior a desverdizado'),
    ('CALIDAD_PALLET', 'Control de calidad posterior a pallet'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('operaciones', '0004_add_etapas_flujo_operativo'),
    ]

    operations = [

        # ----------------------------------------------------------------
        # 1. Campos nuevos en Bin
        # ----------------------------------------------------------------
        migrations.AddField('bin', 'id_bin',
            models.CharField(blank=True, default='', help_text='Codigo interno generado: YYYYMMDD-0001', max_length=20)),
        migrations.AddField('bin', 'contador_incremental',
            models.IntegerField(default=0)),
        migrations.AddField('bin', 'fecha_cosecha',
            models.DateField(blank=True, null=True)),
        migrations.AddField('bin', 'codigo_productor',
            models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField('bin', 'nombre_productor',
            models.CharField(blank=True, default='', max_length=100)),
        migrations.AddField('bin', 'codigo_sag_csg',
            models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField('bin', 'codigo_sag_csp',
            models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField('bin', 'codigo_sdp',
            models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField('bin', 'tipo_cultivo',
            models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField('bin', 'variedad_fruta',
            models.CharField(blank=True, default='', max_length=100)),
        migrations.AddField('bin', 'numero_cuartel',
            models.CharField(blank=True, default='', max_length=20)),
        migrations.AddField('bin', 'nombre_cuartel',
            models.CharField(blank=True, default='', max_length=100)),
        migrations.AddField('bin', 'predio',
            models.CharField(blank=True, default='', max_length=100)),
        migrations.AddField('bin', 'sector',
            models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField('bin', 'lote_productor',
            models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField('bin', 'color',
            models.CharField(blank=True, default='', max_length=30)),
        migrations.AddField('bin', 'estado_fisico',
            models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField('bin', 'a_o_r',
            models.CharField(blank=True, choices=[('aprobado', 'Aprobado'), ('objetado', 'Objetado'), ('rechazado', 'Rechazado')], default='', max_length=10)),
        migrations.AddField('bin', 'n_guia',
            models.CharField(blank=True, default='', max_length=30)),
        migrations.AddField('bin', 'transporte',
            models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField('bin', 'capataz',
            models.CharField(blank=True, default='', max_length=100)),
        migrations.AddField('bin', 'codigo_contratista',
            models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField('bin', 'nombre_contratista',
            models.CharField(blank=True, default='', max_length=100)),
        migrations.AddField('bin', 'hora_recepcion',
            models.CharField(blank=True, default='', help_text='Formato HH:mm', max_length=5)),
        migrations.AddField('bin', 'kilos_bruto_ingreso',
            models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField('bin', 'kilos_neto_ingreso',
            models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField('bin', 'n_cajas_campo',
            models.IntegerField(blank=True, null=True)),
        migrations.AddField('bin', 'observaciones',
            models.TextField(blank=True, default='')),
        migrations.AddField('bin', 'rol',
            models.CharField(blank=True, default='', help_text='Perfil del usuario que registra', max_length=50)),
        migrations.AddIndex('bin',
            models.Index(fields=['fecha_cosecha'], name='ix_bin_fecha_cosecha')),

        # ----------------------------------------------------------------
        # 2. Campos nuevos en Lote
        # ----------------------------------------------------------------
        migrations.AddField('lote', 'id_lote_planta',
            models.CharField(blank=True, default='', help_text='Codigo interno generado: YYYYMMDD-L0001', max_length=20)),
        migrations.AddField('lote', 'contador_incremental',
            models.IntegerField(default=0)),
        migrations.AddField('lote', 'fecha_conformacion',
            models.DateField(blank=True, null=True)),
        migrations.AddField('lote', 'cantidad_bins',
            models.IntegerField(default=0)),
        migrations.AddField('lote', 'kilos_bruto_conformacion',
            models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField('lote', 'kilos_neto_conformacion',
            models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField('lote', 'requiere_desverdizado',
            models.BooleanField(default=False)),
        migrations.AddField('lote', 'disponibilidad_camara_desverdizado',
            models.CharField(
                blank=True,
                choices=[('disponible', 'Disponible'), ('no_disponible', 'No disponible'), ('no_aplica', 'No aplica')],
                help_text='Nullable. Solo aplica si requiere_desverdizado=True.',
                max_length=20,
                null=True,
            )),
        migrations.AddField('lote', 'rol',
            models.CharField(blank=True, default='', help_text='Perfil del usuario que registra', max_length=50)),

        # ----------------------------------------------------------------
        # 3. Campos nuevos en Pallet
        # ----------------------------------------------------------------
        migrations.AddField('pallet', 'id_pallet',
            models.CharField(blank=True, default='', help_text='Codigo interno generado: YYYYMMDD-P0001', max_length=20)),
        migrations.AddField('pallet', 'contador_incremental',
            models.IntegerField(default=0)),
        migrations.AddField('pallet', 'fecha',
            models.DateField(blank=True, null=True)),
        migrations.AddField('pallet', 'hora',
            models.CharField(blank=True, default='', help_text='Formato HH:mm', max_length=5)),
        migrations.AddField('pallet', 'tipo_caja',
            models.CharField(blank=True, default='', max_length=50)),
        migrations.AddField('pallet', 'cajas_por_pallet',
            models.IntegerField(blank=True, null=True)),
        migrations.AddField('pallet', 'peso_total_kg',
            models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField('pallet', 'destino_mercado',
            models.CharField(blank=True, default='', max_length=100)),
        migrations.AddField('pallet', 'rol',
            models.CharField(blank=True, default='', help_text='Perfil del usuario que registra', max_length=50)),

        # ----------------------------------------------------------------
        # 4. Actualizar TipoEvento con nuevas opciones
        # ----------------------------------------------------------------
        migrations.AlterField(
            model_name='registroetapa',
            name='tipo_evento',
            field=models.CharField(
                choices=TIPO_EVENTO_CHOICES,
                db_index=True,
                max_length=40,
            ),
        ),

        # ----------------------------------------------------------------
        # 5. Crear CamaraMantencion
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name='CamaraMantencion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_system', models.CharField(blank=True, default='local', max_length=50)),
                ('source_event_id', models.CharField(blank=True, db_index=True, default='', max_length=120)),
                ('operator_code', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('lote', models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='camara_mantencion',
                    to='operaciones.lote',
                )),
                ('camara_numero', models.CharField(blank=True, default='', max_length=20)),
                ('fecha_ingreso', models.DateField(blank=True, null=True)),
                ('hora_ingreso', models.CharField(blank=True, default='', help_text='Formato HH:mm', max_length=5)),
                ('fecha_salida', models.DateField(blank=True, null=True)),
                ('hora_salida', models.CharField(blank=True, default='', max_length=5)),
                ('temperatura_camara', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('humedad_relativa', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('observaciones', models.TextField(blank=True, default='')),
                ('rol', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={'db_table': 'operaciones_camara_mantencion', 'ordering': ['-created_at']},
        ),

        # ----------------------------------------------------------------
        # 6. Crear Desverdizado
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name='Desverdizado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_system', models.CharField(blank=True, default='local', max_length=50)),
                ('source_event_id', models.CharField(blank=True, db_index=True, default='', max_length=120)),
                ('operator_code', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('lote', models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='desverdizado',
                    to='operaciones.lote',
                )),
                ('fecha_ingreso', models.DateField(blank=True, null=True)),
                ('hora_ingreso', models.CharField(blank=True, default='', help_text='Formato HH:mm', max_length=5)),
                ('fecha_salida', models.DateField(blank=True, null=True)),
                ('hora_salida', models.CharField(blank=True, default='', max_length=5)),
                ('kilos_enviados_terreno', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('kilos_recepcionados', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('kilos_procesados', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('kilos_bruto_salida', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('kilos_neto_salida', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('color_salida', models.CharField(blank=True, default='', max_length=30)),
                ('proceso', models.CharField(blank=True, default='', max_length=100)),
                ('fecha_proceso', models.DateField(blank=True, null=True)),
                ('sector', models.CharField(blank=True, default='', max_length=50)),
                ('cuartel', models.CharField(blank=True, default='', max_length=50)),
                ('rol', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={'db_table': 'operaciones_desverdizado', 'ordering': ['-created_at']},
        ),

        # ----------------------------------------------------------------
        # 7. Crear CalidadDesverdizado
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name='CalidadDesverdizado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_system', models.CharField(blank=True, default='local', max_length=50)),
                ('source_event_id', models.CharField(blank=True, db_index=True, default='', max_length=120)),
                ('operator_code', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('lote', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='calidad_desverdizado',
                    to='operaciones.lote',
                )),
                ('fecha', models.DateField(blank=True, null=True)),
                ('hora', models.CharField(blank=True, default='', help_text='Formato HH:mm', max_length=5)),
                ('temperatura_fruta', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('color_evaluado', models.CharField(blank=True, default='', max_length=30)),
                ('estado_visual', models.CharField(blank=True, default='', max_length=50)),
                ('presencia_defectos', models.BooleanField(blank=True, null=True)),
                ('descripcion_defectos', models.TextField(blank=True, default='')),
                ('aprobado', models.BooleanField(blank=True, null=True)),
                ('observaciones', models.TextField(blank=True, default='')),
                ('rol', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={'db_table': 'operaciones_calidad_desverdizado', 'ordering': ['-created_at']},
        ),

        # ----------------------------------------------------------------
        # 8. Crear IngresoAPacking
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name='IngresoAPacking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_system', models.CharField(blank=True, default='local', max_length=50)),
                ('source_event_id', models.CharField(blank=True, db_index=True, default='', max_length=120)),
                ('operator_code', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('lote', models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='ingreso_packing',
                    to='operaciones.lote',
                )),
                ('fecha_ingreso', models.DateField(blank=True, null=True)),
                ('hora_ingreso', models.CharField(blank=True, default='', help_text='Formato HH:mm', max_length=5)),
                ('kilos_bruto_ingreso_packing', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('kilos_neto_ingreso_packing', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('via_desverdizado', models.BooleanField(default=False)),
                ('observaciones', models.TextField(blank=True, default='')),
                ('rol', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={'db_table': 'operaciones_ingreso_packing', 'ordering': ['-created_at']},
        ),

        # ----------------------------------------------------------------
        # 9. Crear RegistroPacking
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name='RegistroPacking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_system', models.CharField(blank=True, default='local', max_length=50)),
                ('source_event_id', models.CharField(blank=True, db_index=True, default='', max_length=120)),
                ('operator_code', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('lote', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='registros_packing',
                    to='operaciones.lote',
                )),
                ('fecha', models.DateField(blank=True, null=True)),
                ('hora_inicio', models.CharField(blank=True, default='', help_text='Formato HH:mm', max_length=5)),
                ('linea_proceso', models.CharField(blank=True, default='', max_length=50)),
                ('categoria_calidad', models.CharField(blank=True, default='', max_length=50)),
                ('calibre', models.CharField(blank=True, default='', max_length=20)),
                ('tipo_envase', models.CharField(blank=True, default='', max_length=50)),
                ('cantidad_cajas_producidas', models.IntegerField(blank=True, null=True)),
                ('peso_promedio_caja_kg', models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True)),
                ('merma_seleccion_pct', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('rol', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={'db_table': 'operaciones_registro_packing', 'ordering': ['-created_at']},
        ),

        # ----------------------------------------------------------------
        # 10. Crear ControlProcesoPacking
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name='ControlProcesoPacking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_system', models.CharField(blank=True, default='local', max_length=50)),
                ('source_event_id', models.CharField(blank=True, db_index=True, default='', max_length=120)),
                ('operator_code', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('lote', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='control_proceso_packing',
                    to='operaciones.lote',
                )),
                ('fecha', models.DateField(blank=True, null=True)),
                ('hora', models.CharField(blank=True, default='', help_text='Formato HH:mm', max_length=5)),
                ('n_bins_procesados', models.IntegerField(blank=True, null=True)),
                ('velocidad_volcador', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('obs_volcador', models.CharField(blank=True, default='', max_length=200)),
                ('temp_agua_tina', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('cloro_libre_ppm', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('ph_agua', models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ('tiempo_inmersion_seg', models.IntegerField(blank=True, null=True)),
                ('recambio_agua', models.BooleanField(blank=True, null=True)),
                ('temp_aire_secado', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('velocidad_ventiladores', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('fruta_sale_seca', models.BooleanField(blank=True, null=True)),
                ('tipo_cera', models.CharField(blank=True, default='', max_length=50)),
                ('dosis_cera_ml_min', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('temp_cera', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('cobertura_uniforme', models.BooleanField(blank=True, null=True)),
                ('n_operarios_seleccion', models.IntegerField(blank=True, null=True)),
                ('fruta_dano_condicion_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('fruta_dano_calidad_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('fruta_pudricion_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('merma_total_seleccion_kg', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('equipo_calibrador', models.CharField(blank=True, default='', max_length=50)),
                ('calibre_predominante', models.CharField(blank=True, default='', max_length=20)),
                ('pct_calibre_export', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('pct_calibres_menores', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('tipo_caja', models.CharField(blank=True, default='', max_length=50)),
                ('peso_promedio_caja_kg', models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True)),
                ('n_cajas_producidas', models.IntegerField(blank=True, null=True)),
                ('rendimiento_lote_pct', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('observaciones_generales', models.TextField(blank=True, default='')),
                ('rol', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={'db_table': 'operaciones_control_proceso_packing', 'ordering': ['-created_at']},
        ),

        # ----------------------------------------------------------------
        # 11. Crear CalidadPallet
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name='CalidadPallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_system', models.CharField(blank=True, default='local', max_length=50)),
                ('source_event_id', models.CharField(blank=True, db_index=True, default='', max_length=120)),
                ('operator_code', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('pallet', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='calidad_pallet',
                    to='operaciones.pallet',
                )),
                ('fecha', models.DateField(blank=True, null=True)),
                ('hora', models.CharField(blank=True, default='', help_text='Formato HH:mm', max_length=5)),
                ('temperatura_fruta', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('peso_caja_muestra', models.DecimalField(blank=True, decimal_places=3, max_digits=8, null=True)),
                ('estado_embalaje', models.CharField(blank=True, default='', max_length=50)),
                ('estado_visual_fruta', models.CharField(blank=True, default='', max_length=50)),
                ('presencia_defectos', models.BooleanField(blank=True, null=True)),
                ('descripcion_defectos', models.TextField(blank=True, default='')),
                ('aprobado', models.BooleanField(blank=True, null=True)),
                ('observaciones', models.TextField(blank=True, default='')),
                ('rol', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={'db_table': 'operaciones_calidad_pallet', 'ordering': ['-created_at']},
        ),

        # ----------------------------------------------------------------
        # 12. Crear CamaraFrio
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name='CamaraFrio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_system', models.CharField(blank=True, default='local', max_length=50)),
                ('source_event_id', models.CharField(blank=True, db_index=True, default='', max_length=120)),
                ('operator_code', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('pallet', models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='camara_frio',
                    to='operaciones.pallet',
                )),
                ('camara_numero', models.CharField(blank=True, default='', max_length=20)),
                ('temperatura_camara', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('humedad_relativa', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('fecha_ingreso', models.DateField(blank=True, null=True)),
                ('hora_ingreso', models.CharField(blank=True, default='', help_text='Formato HH:mm', max_length=5)),
                ('fecha_salida', models.DateField(blank=True, null=True)),
                ('hora_salida', models.CharField(blank=True, default='', max_length=5)),
                ('destino_despacho', models.CharField(blank=True, default='', max_length=100)),
                ('rol', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={'db_table': 'operaciones_camara_frio', 'ordering': ['-created_at']},
        ),

        # ----------------------------------------------------------------
        # 13. Crear MedicionTemperaturaSalida
        # ----------------------------------------------------------------
        migrations.CreateModel(
            name='MedicionTemperaturaSalida',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('source_system', models.CharField(blank=True, default='local', max_length=50)),
                ('source_event_id', models.CharField(blank=True, db_index=True, default='', max_length=120)),
                ('operator_code', models.CharField(blank=True, db_index=True, default='', max_length=50)),
                ('pallet', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='mediciones_temperatura',
                    to='operaciones.pallet',
                )),
                ('fecha', models.DateField(blank=True, null=True)),
                ('hora', models.CharField(blank=True, default='', help_text='Formato HH:mm', max_length=5)),
                ('temperatura_pallet', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('punto_medicion', models.CharField(blank=True, default='', max_length=100)),
                ('dentro_rango', models.BooleanField(blank=True, null=True)),
                ('observaciones', models.TextField(blank=True, default='')),
                ('rol', models.CharField(blank=True, default='', max_length=50)),
            ],
            options={'db_table': 'operaciones_medicion_temperatura_salida', 'ordering': ['-created_at']},
        ),
    ]
