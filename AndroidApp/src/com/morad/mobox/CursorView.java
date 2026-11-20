package com.morad.mobox;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.View;

public final class CursorView extends View {
    private final Paint fill = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint stroke = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path arrow = new Path();

    public CursorView(Context ctx) {
        super(ctx);
        float d = ctx.getResources().getDisplayMetrics().density;
        fill.setColor(Color.parseColor("#F4B80C"));
        fill.setStyle(Paint.Style.FILL);
        stroke.setColor(Color.parseColor("#0D0F14"));
        stroke.setStyle(Paint.Style.STROKE);
        stroke.setStrokeWidth(2f * d);

        float s = 24f * d;
        float p2 = 2f * d;
        arrow.moveTo(p2, p2);
        arrow.lineTo(p2, s * 0.85f);
        arrow.lineTo(s * 0.30f, s * 0.65f);
        arrow.lineTo(s * 0.48f, s * 0.95f);
        arrow.lineTo(s * 0.62f, s * 0.88f);
        arrow.lineTo(s * 0.44f, s * 0.58f);
        arrow.lineTo(s * 0.78f, s * 0.55f);
        arrow.close();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        canvas.drawPath(arrow, fill);
        canvas.drawPath(arrow, stroke);
    }
}
