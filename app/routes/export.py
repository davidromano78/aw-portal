import io
import zipfile

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from app.pdf.sacs_template import generate_sacs_pdf
from app.pdf.tcc_template import generate_tcc_pdf
from app.services import get_report

router = APIRouter()


@router.get("/reports/{report_id}/download/sacs")
def download_sacs(report_id: int):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    pdf_bytes = generate_sacs_pdf(report["client"], report)
    filename = f"SACS_{report['client']['display_name'].replace(' ', '_')}_{report['report_date']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/{report_id}/download/tcc")
def download_tcc(report_id: int):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    pdf_bytes = generate_tcc_pdf(report["client"], report)
    filename = f"TCC_{report['client']['display_name'].replace(' ', '_')}_{report['report_date']}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/{report_id}/download/all")
def download_all(report_id: int):
    report = get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    sacs_bytes = generate_sacs_pdf(report["client"], report)
    tcc_bytes = generate_tcc_pdf(report["client"], report)
    base = report["client"]["display_name"].replace(" ", "_")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"SACS_{base}_{report['report_date']}.pdf", sacs_bytes)
        zf.writestr(f"TCC_{base}_{report['report_date']}.pdf", tcc_bytes)
    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="Reports_{base}_{report["report_date"]}.zip"'
        },
    )
