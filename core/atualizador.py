import os
import sys
import requests
import zipfile
import io
import shutil
import tempfile
import subprocess
import traceback
import ctypes
import re
from tkinter import Toplevel, Label, ttk, messagebox
from core.versao import VERSAO_ATUAL

GITHUB_RAW_VERSAO_URL = "https://raw.githubusercontent.com/A1cantar4/gerador-de-gabaritos-personalizados/refs/heads/master/core/versao.py"
GITHUB_ZIP_EXE_URL = "https://github.com/A1cantar4/gerador-de-gabaritos-personalizados/releases/latest/download/GabaritoApp.zip"
GITHUB_ZIP_SOURCE_URL = "https://github.com/A1cantar4/gerador-de-gabaritos-personalizados/archive/refs/heads/master.zip"
IGNORAR_ARQUIVOS = [
    "config.json", "log_erro.txt", "__pycache__", ".gitignore", ".gitattributes", ".git", ".github"
]

# === Utilitários ===

def is_frozen():
    return getattr(sys, 'frozen', False)

def tem_permissao_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def registrar_erro(e):
    erro = traceback.format_exc()
    try:
        with open("log_erro.txt", "a", encoding="utf-8") as f:
            f.write(erro + "\n")
    except:
        pass
    try:
        messagebox.showerror("Erro", f"Ocorreu um erro:\n{type(e).__name__}: {e}")
    except:
        pass

def extrair_versao(codigo_remoto):
    match = re.search(r'VERSAO_ATUAL\s*=\s*[\'"](.+?)[\'"]', codigo_remoto)
    return match.group(1) if match else None

def mostrar_progresso(etapa_texto, percent, barra, status):
    barra['value'] = percent
    status.config(text=etapa_texto)
    barra.update()
    status.update()

def criar_reiniciador(nome_atual):
    conteudo = f"""@echo off
timeout /t 2 >nul
if exist "antigo_backup.exe" del "antigo_backup.exe" >nul
if exist "{nome_atual}" ren "{nome_atual}" antigo_backup.exe
move /Y novo_temp.exe "{nome_atual}" >nul
start "" "{nome_atual}"
exit
"""
    with open("reiniciador.bat", "w", encoding="utf-8") as f:
        f.write(conteudo)
    subprocess.Popen(["cmd", "/c", "start", "reiniciador.bat"])

def atualizar_codigo_fonte_com_progresso(root):
    try:
        janela = Toplevel(root)
        janela.title("Atualizando...")
        janela.geometry("400x100")
        janela.resizable(False, False)

        status = Label(janela, text="Iniciando...", anchor="w")
        status.pack(pady=5, padx=10, anchor="w")

        barra = ttk.Progressbar(janela, orient="horizontal", length=380, mode="determinate")
        barra.pack(pady=10, padx=10)

        janela.grab_set()
        janela.update()

        mostrar_progresso("Baixando código fonte...", 10, barra, status)
        response = requests.get(GITHUB_ZIP_SOURCE_URL)
        if response.status_code != 200:
            raise Exception("Não foi possível baixar o código-fonte.")

        if not zipfile.is_zipfile(io.BytesIO(response.content)):
            raise Exception("Arquivo ZIP do GitHub inválido ou corrompido.")

        mostrar_progresso("Extraindo arquivos...", 30, barra, status)
        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            temp_folder = tempfile.mkdtemp()
            zip_ref.extractall(temp_folder)

            extraido = os.path.join(temp_folder, "gerador-de-gabaritos-personalizados-master")

            for item in os.listdir(extraido):
                if item in IGNORAR_ARQUIVOS or item.startswith("."):
                    continue

                src = os.path.join(extraido, item)
                dest = os.path.join(".", item)

                if os.path.exists(dest):
                    try:
                        if os.path.isfile(dest) or os.path.islink(dest):
                            os.remove(dest)
                        else:
                            shutil.rmtree(dest)
                    except:
                        continue

                try:
                    if os.path.isfile(src):
                        shutil.copy2(src, dest)
                    else:
                        shutil.copytree(src, dest)
                except:
                    continue

        with open("versao_antiga.txt", "w", encoding="utf-8") as f:
            f.write(VERSAO_ATUAL)

        mostrar_progresso("Atualização concluída.", 100, barra, status)
        janela.destroy()
        return True

    except Exception as e:
        registrar_erro(e)
        return False

def atualizar_executavel_com_progresso(root):
    try:
        janela = Toplevel(root)
        janela.title("Atualizando...")
        janela.geometry("400x100")
        janela.resizable(False, False)

        status = Label(janela, text="Iniciando...", anchor="w")
        status.pack(pady=5, padx=10, anchor="w")

        barra = ttk.Progressbar(janela, orient="horizontal", length=380, mode="determinate")
        barra.pack(pady=10, padx=10)

        janela.grab_set()
        janela.update()

        mostrar_progresso("Baixando atualização...", 10, barra, status)
        response = requests.get(GITHUB_ZIP_EXE_URL, stream=True)
        if response.status_code != 200:
            raise Exception("Não foi possível baixar a atualização.")

        zip_data = io.BytesIO(response.content)
        mostrar_progresso("Download concluído", 30, barra, status)

        with zipfile.ZipFile(zip_data) as z:
            exe_temp = "novo_temp.exe"
            for nome in z.namelist():
                if nome.endswith(".exe"):
                    with open(exe_temp, "wb") as f:
                        f.write(z.read(nome))
                    break
            else:
                raise Exception("Executável não encontrado no ZIP.")

        mostrar_progresso("Extração concluída", 60, barra, status)

        nome_atual = os.path.basename(sys.executable)
        mostrar_progresso("Finalizando...", 100, barra, status)
        janela.destroy()

        criar_reiniciador(nome_atual)
        return True

    except Exception as e:
        registrar_erro(e)
        return False

def verificar_e_atualizar(mostrar_mensagem=False, root=None):
    try:
        r = requests.get(GITHUB_RAW_VERSAO_URL, timeout=5)
        if r.status_code != 200:
            if mostrar_mensagem:
                messagebox.showinfo("Offline", f"Não foi possível verificar atualizações.\nVocê está no modo offline (versão {VERSAO_ATUAL}).")
            return

        versao_online = extrair_versao(r.text)
        if versao_online and versao_online != VERSAO_ATUAL:
            if messagebox.askyesno("Atualização disponível", f"Versão {versao_online} disponível. Atualizar agora?"):

                if not tem_permissao_admin():
                    resposta = messagebox.askyesno("Permissão necessária", "É necessário executar como administrador. Deseja continuar?")
                    if resposta:
                        ctypes.windll.shell32.ShellExecuteW(
                            None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1
                        )
                    sys.exit()

                if is_frozen():
                    sucesso = atualizar_executavel_com_progresso(root or Toplevel())
                else:
                    sucesso = atualizar_codigo_fonte_com_progresso(root or Toplevel())

                if sucesso:
                    messagebox.showinfo("Atualizado", "Atualização concluída. O aplicativo será reiniciado.")
                    sys.exit()
                else:
                    messagebox.showerror("Erro", "Erro durante a atualização.")
        elif mostrar_mensagem:
            messagebox.showinfo("Atualização", "Você já está com a versão mais recente.")

    except requests.exceptions.RequestException:
        if mostrar_mensagem:
            messagebox.showinfo("Offline", f"Não foi possível verificar atualizações.\nVocê está no modo offline (versão {VERSAO_ATUAL}).")
    except Exception as e:
        registrar_erro(e)
        if mostrar_mensagem:
            messagebox.showerror("Erro", "Erro ao verificar atualização.")