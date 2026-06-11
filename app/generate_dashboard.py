from services.dashboard_service import DashboardService
 
if __name__ == "__main__":
    caminho = DashboardService.gerar()
    print(f"\nAbra no navegador: file://{caminho}")
 