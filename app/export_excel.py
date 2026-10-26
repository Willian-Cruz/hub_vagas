from services.export_service import ExportService

if __name__ == "__main__":
    caminho = ExportService.exportar()
    print(f"\nArquivo gerado em: {caminho}")
