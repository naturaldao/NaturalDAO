# fetch_papers.ps1
# 抓取 data/pol2_mapping.csv 中每篇论文的 arXiv 元数据、许可证与 PDF。
# 适用：Windows PowerShell 5.1 或 PowerShell 7+。
#
# 用法（在本目录根部运行）：
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\fetch_papers.ps1
#   可选参数：-Proxy "http://127.0.0.1:7890"（经本地代理访问 arXiv；默认不走代理）
#
# 输出：
#   data\sources\arxiv_meta.csv   标题、作者、日期、分类、许可证、摘要
#   papers\                        Creative Commons 许可的 PDF —— 纳入仓库
#   papers\_local\                 arXiv 默认许可的 PDF —— 不可再分发，仅供本地阅读，已被 .gitignore 忽略
# 之后运行：python scripts/build_catalog.py ; python scripts/check.py

param(
    [string]$Proxy = ""
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$PdfDir = Join-Path $Root 'papers'
$LocalDir = Join-Path $PdfDir '_local'
$MetaOut = Join-Path $Root 'data\sources\arxiv_meta.csv'

$Ids = @(Import-Csv (Join-Path $Root 'data\pol2_mapping.csv') -Encoding UTF8 | ForEach-Object { $_.arxiv_id })

$Common = @{ UseBasicParsing = $true; TimeoutSec = 120; Headers = @{ 'User-Agent' = 'NaturalDAO-PoL-literature/1.0' } }
if ($Proxy) { $Common['Proxy'] = $Proxy }

New-Item -ItemType Directory -Force -Path $PdfDir, $LocalDir, (Split-Path $MetaOut) | Out-Null

# ---------- 1. 元数据：arXiv API 一次取回 ----------
Write-Host "arXiv API: 取回 $($Ids.Count) 篇论文的元数据 ..."
$apiUrl = "https://export.arxiv.org/api/query?id_list=$($Ids -join ',')&max_results=100"
$resp = Invoke-WebRequest -Uri $apiUrl @Common
$xml = [xml]$resp.Content
$ns = New-Object Xml.XmlNamespaceManager($xml.NameTable)
$ns.AddNamespace('a', 'http://www.w3.org/2005/Atom')
$ns.AddNamespace('arxiv', 'http://arxiv.org/schemas/atom')

$Meta = @{}
foreach ($e in $xml.SelectNodes('//a:entry', $ns)) {
    $full = $e.SelectSingleNode('a:id', $ns).InnerText          # http://arxiv.org/abs/2609.xxxxxvN
    $id   = ($full -replace '^.*/abs/', '') -replace 'v\d+$', ''
    $Meta[$id] = [ordered]@{
        arxiv_id         = $id
        version          = ($full -replace '^.*/abs/', '')
        title            = ($e.SelectSingleNode('a:title', $ns).InnerText -replace '\s+', ' ').Trim()
        authors          = (($e.SelectNodes('a:author/a:name', $ns) | ForEach-Object { $_.InnerText }) -join '; ')
        published        = $e.SelectSingleNode('a:published', $ns).InnerText.Substring(0, 10)
        updated          = $e.SelectSingleNode('a:updated', $ns).InnerText.Substring(0, 10)
        primary_category = $e.SelectSingleNode('arxiv:primary_category', $ns).GetAttribute('term')
        comment          = if ($e.SelectSingleNode('arxiv:comment', $ns)) { ($e.SelectSingleNode('arxiv:comment', $ns).InnerText -replace '\s+', ' ').Trim() } else { '' }
        abstract         = ($e.SelectSingleNode('a:summary', $ns).InnerText -replace '\s+', ' ').Trim()
        license_url      = ''
        redistributable  = ''
        pdf_status       = ''
    }
}
Write-Host "  取回 $($Meta.Count) 条。"
Start-Sleep -Seconds 3

# ---------- 2. 逐篇：许可证 + PDF ----------
$i = 0
foreach ($id in $Ids) {
    $i++
    if (-not $Meta.ContainsKey($id)) {
        Write-Warning "[$i/$($Ids.Count)] $id 不在 API 返回结果中，跳过"
        $Meta[$id] = [ordered]@{ arxiv_id = $id; pdf_status = 'not_in_api' }
        continue
    }
    $m = $Meta[$id]
    Write-Host "[$i/$($Ids.Count)] $id  $($m.title.Substring(0, [Math]::Min(60, $m.title.Length)))"

    # 许可证：摘要页上 title="Rights to this article" 的链接
    try {
        $abs = (Invoke-WebRequest -Uri "https://arxiv.org/abs/$id" @Common).Content
        $mm = [regex]::Match($abs, 'href="([^"]+)"[^>]*title="Rights to this article"|title="Rights to this article"[^>]*href="([^"]+)"')
        if ($mm.Success) { $m.license_url = if ($mm.Groups[1].Value) { $mm.Groups[1].Value } else { $mm.Groups[2].Value } }
    } catch { Write-Warning "  许可证读取失败: $($_.Exception.Message)" }
    $isCC = $m.license_url -match 'creativecommons\.org/(licenses|publicdomain)/'
    $m.redistributable = [string]$isCC
    Start-Sleep -Seconds 3

    # PDF
    $target = if ($isCC) { Join-Path $PdfDir "$id.pdf" } else { Join-Path $LocalDir "$id.pdf" }
    if (Test-Path $target) { $m.pdf_status = 'exists'; continue }
    try {
        Invoke-WebRequest -Uri "https://arxiv.org/pdf/$id" -OutFile $target @Common
        $m.pdf_status = if ($isCC) { 'papers' } else { 'papers/_local' }
    } catch {
        Write-Warning "  PDF 下载失败: $($_.Exception.Message)"
        $m.pdf_status = 'failed'
    }
    Start-Sleep -Seconds 3
}

# ---------- 3. 导出 ----------
$rows = foreach ($id in $Ids) { [pscustomobject]$Meta[$id] }
$rows | Export-Csv -Path $MetaOut -NoTypeInformation -Encoding UTF8

$cc  = @($rows | Where-Object { $_.redistributable -eq 'True' }).Count
$loc = @($rows | Where-Object { $_.pdf_status -eq 'papers/_local' }).Count
$bad = @($rows | Where-Object { $_.pdf_status -in 'failed', 'not_in_api' }).Count
Write-Host ""
Write-Host "完成：可转载 PDF $cc 篇（papers\），仅本地 PDF $loc 篇（papers\_local\），失败 $bad 篇。"
Write-Host "元数据：$MetaOut"
Write-Host "下一步：python scripts/build_catalog.py ; python scripts/check.py"
